# social.py - Подарки и торговля
"""Система подарков и обмена предметами между игроками"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from utils.embed_builder import EmbedBuilder, Colors


class TradeView(discord.ui.View):
    """View для подтверждения обмена"""
    
    def __init__(self, initiator, partner, initiator_offer, partner_offer, social_cog):
        super().__init__(timeout=120)
        self.initiator = initiator
        self.partner = partner
        self.initiator_offer = initiator_offer
        self.partner_offer = partner_offer
        self.social_cog = social_cog
        self.initiator_accepted = False
        self.partner_accepted = False
    
    @discord.ui.button(label="Подтвердить обмен", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.initiator.id:
            self.initiator_accepted = True
        elif interaction.user.id == self.partner.id:
            self.partner_accepted = True
        else:
            await interaction.response.send_message("❌ Это не ваш обмен!", ephemeral=True)
            return
        
        # Если оба подтвердили
        if self.initiator_accepted and self.partner_accepted:
            # Проверяем балансы
            if self.initiator_offer > 0:
                balance1 = self.social_cog._get_economy_balance(str(self.initiator.id))
                if balance1 < self.initiator_offer:
                    await interaction.response.send_message("❌ У инициатора недостаточно средств!", ephemeral=True)
                    return
            
            if self.partner_offer > 0:
                balance2 = self.social_cog._get_economy_balance(str(self.partner.id))
                if balance2 < self.partner_offer:
                    await interaction.response.send_message("❌ У партнёра недостаточно средств!", ephemeral=True)
                    return
            
            # Выполняем обмен
            if self.initiator_offer > 0:
                self.social_cog._update_economy_balance(str(self.initiator.id), -self.initiator_offer)
                self.social_cog._update_economy_balance(str(self.partner.id), self.initiator_offer)
            
            if self.partner_offer > 0:
                self.social_cog._update_economy_balance(str(self.partner.id), -self.partner_offer)
                self.social_cog._update_economy_balance(str(self.initiator.id), self.partner_offer)
            
            # Отключаем кнопки
            for item in self.children:
                item.disabled = True
            
            em = discord.Embed(
                title="✅ Обмен Завершён!",
                description=f"{self.initiator.mention} ⇄ {self.partner.mention}",
                color=Colors.SUCCESS
            )
            em.add_field(
                name=f"{self.initiator.display_name} отдал",
                value=f"{self.initiator_offer:,}💎" if self.initiator_offer > 0 else "Ничего",
                inline=True
            )
            em.add_field(
                name=f"{self.partner.display_name} отдал",
                value=f"{self.partner_offer:,}💎" if self.partner_offer > 0 else "Ничего",
                inline=True
            )
            
            await interaction.response.edit_message(embed=em, view=self)
        else:
            # Обновляем статус
            status = []
            if self.initiator_accepted:
                status.append(f"✅ {self.initiator.display_name}")
            else:
                status.append(f"⏳ {self.initiator.display_name}")
            
            if self.partner_accepted:
                status.append(f"✅ {self.partner.display_name}")
            else:
                status.append(f"⏳ {self.partner.display_name}")
            
            em = discord.Embed(
                title="🤝 Обмен",
                description=" | ".join(status),
                color=Colors.PRIMARY
            )
            em.add_field(
                name=f"{self.initiator.display_name} предлагает",
                value=f"{self.initiator_offer:,}💎" if self.initiator_offer > 0 else "Ничего",
                inline=True
            )
            em.add_field(
                name=f"{self.partner.display_name} предлагает",
                value=f"{self.partner_offer:,}💎" if self.partner_offer > 0 else "Ничего",
                inline=True
            )
            em.set_footer(text="Оба игрока должны подтвердить обмен")
            
            await interaction.response.edit_message(embed=em, view=self)
    
    @discord.ui.button(label="Отменить", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.initiator.id, self.partner.id]:
            await interaction.response.send_message("❌ Это не ваш обмен!", ephemeral=True)
            return
        
        for item in self.children:
            item.disabled = True
        
        em = discord.Embed(
            title="❌ Обмен Отменён",
            description=f"{interaction.user.mention} отменил обмен",
            color=Colors.ERROR
        )
        
        await interaction.response.edit_message(embed=em, view=self)


class Social(commands.Cog):
    """Социальные функции"""
    
    def __init__(self, bot):
        self.bot = bot
        self.currency_emoji = "💎"
    
    def _get_economy_balance(self, user_id: str) -> int:
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            return economy_cog._get_user_data(user_id).get('balance', 0)
        return 0
    
    def _update_economy_balance(self, user_id: str, amount: int):
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            economy_cog._update_balance(user_id, amount)
            economy_cog._add_transaction(user_id, "social", amount, "Социальная транзакция")
    
    @app_commands.command(name="gift", description="🎁 Подарить крионы")
    @app_commands.describe(
        user="Кому подарить",
        amount="Сумма подарка"
    )
    async def gift(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Подарить крионы другому пользователю"""
        sender_id = str(interaction.user.id)
        receiver_id = str(user.id)
        
        if amount <= 0:
            await interaction.response.send_message("❌ Сумма должна быть больше 0!", ephemeral=True)
            return
        
        if user.bot:
            await interaction.response.send_message("❌ Нельзя дарить ботам!", ephemeral=True)
            return
        
        if sender_id == receiver_id:
            await interaction.response.send_message("❌ Нельзя дарить самому себе!", ephemeral=True)
            return
        
        # Проверка баланса
        balance = self._get_economy_balance(sender_id)
        if balance < amount:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"У вас: **{balance:,}**{self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Перевод
        self._update_economy_balance(sender_id, -amount)
        self._update_economy_balance(receiver_id, amount)
        
        em = EmbedBuilder.success(
            title="🎁 Подарок Отправлен!",
            description=f"{interaction.user.mention} подарил **{amount:,}**{self.currency_emoji} {user.mention}!",
            user=interaction.user
        )
        em.set_thumbnail(url=user.display_avatar.url)
        
        # Логирование
        logs_cog = self.bot.get_cog('Logs')
        if logs_cog and interaction.guild:
            await logs_cog.log_economy_transaction(
                guild=interaction.guild,
                user=interaction.user,
                transaction_type="Подарок",
                amount=amount,
                details=f"Получатель: {user.display_name}"
            )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="trade", description="🤝 Предложить обмен")
    @app_commands.describe(
        user="С кем обменяться",
        your_offer="Ваше предложение (крионы)",
        their_offer="Их предложение (крионы)"
    )
    async def trade(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member,
        your_offer: int = 0,
        their_offer: int = 0
    ):
        """Предложить обмен другому игроку"""
        if user.bot:
            await interaction.response.send_message("❌ Нельзя обмениваться с ботами!", ephemeral=True)
            return
        
        if interaction.user.id == user.id:
            await interaction.response.send_message("❌ Нельзя обмениваться с самим собой!", ephemeral=True)
            return
        
        if your_offer < 0 or their_offer < 0:
            await interaction.response.send_message("❌ Суммы не могут быть отрицательными!", ephemeral=True)
            return
        
        if your_offer == 0 and their_offer == 0:
            await interaction.response.send_message("❌ Хотя бы одна сторона должна что-то предложить!", ephemeral=True)
            return
        
        # Проверка баланса инициатора
        if your_offer > 0:
            balance = self._get_economy_balance(str(interaction.user.id))
            if balance < your_offer:
                em = EmbedBuilder.error(
                    title="Недостаточно средств!",
                    description=f"У вас: **{balance:,}**{self.currency_emoji}",
                    user=interaction.user
                )
                await interaction.response.send_message(embed=em, ephemeral=True)
                return
        
        # Создаём обмен
        view = TradeView(interaction.user, user, your_offer, their_offer, self)
        
        em = discord.Embed(
            title="🤝 Предложение Обмена",
            description=f"{interaction.user.mention} предлагает обмен {user.mention}",
            color=Colors.PRIMARY
        )
        em.add_field(
            name=f"{interaction.user.display_name} предлагает",
            value=f"{your_offer:,}💎" if your_offer > 0 else "Ничего",
            inline=True
        )
        em.add_field(
            name=f"{user.display_name} должен дать",
            value=f"{their_offer:,}💎" if their_offer > 0 else "Ничего",
            inline=True
        )
        em.set_footer(text="Оба игрока должны подтвердить обмен")
        
        await interaction.response.send_message(embed=em, view=view)


async def setup(bot):
    await bot.add_cog(Social(bot))
