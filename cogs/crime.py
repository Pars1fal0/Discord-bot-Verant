# crime.py - Rob/Crime система
"""Система преступлений: грабежи, преступления, тюрьма"""
import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime, timedelta
from utils.embed_builder import EmbedBuilder, Colors


class Crime(commands.Cog):
    """Система преступлений"""
    
    def __init__(self, bot):
        self.bot = bot
        self.currency_emoji = "💎"
        self.rob_cooldowns = {}  # user_id: timestamp
        self.jail_time = {}  # user_id: release_time
    
    def _get_economy_balance(self, user_id: str) -> int:
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            return economy_cog._get_user_data(user_id).get('balance', 0)
        return 0
    
    def _update_economy_balance(self, user_id: str, amount: int):
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            economy_cog._update_balance(user_id, amount)
            economy_cog._add_transaction(user_id, "crime", amount, "Преступление")
    
    def _is_in_jail(self, user_id: str) -> tuple:
        """Проверить в тюрьме ли пользователь"""
        if user_id in self.jail_time:
            release_time = self.jail_time[user_id]
            if datetime.now() < release_time:
                time_left = release_time - datetime.now()
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                return True, f"{hours}ч {minutes}м"
            else:
                del self.jail_time[user_id]
        return False, ""
    
    @app_commands.command(name="rob", description="🔫 Ограбить пользователя")
    @app_commands.describe(user="Цель для ограбления")
    async def rob(self, interaction: discord.Interaction, user: discord.Member):
        """Попытаться ограбить другого пользователя"""
        robber_id = str(interaction.user.id)
        target_id = str(user.id)
        
        # Проверки
        if user.bot:
            await interaction.response.send_message("❌ Нельзя грабить ботов!", ephemeral=True)
            return
        
        if robber_id == target_id:
            await interaction.response.send_message("❌ Нельзя грабить самого себя!", ephemeral=True)
            return
        
        # Проверка тюрьмы
        in_jail, time_left = self._is_in_jail(robber_id)
        if in_jail:
            await interaction.response.send_message(f"🔒 Вы в тюрьме! Освобождение через: {time_left}", ephemeral=True)
            return
        
        # Проверка кулдауна (8 часов)
        if robber_id in self.rob_cooldowns:
            last_rob = self.rob_cooldowns[robber_id]
            time_passed = (datetime.now() - last_rob).total_seconds()
            if time_passed < 28800:  # 8 часов
                time_left = timedelta(seconds=28800 - time_passed)
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"⏰ Следующее ограбление через: {hours}ч {minutes}м",
                    ephemeral=True
                )
                return
        
        # Проверка баланса жертвы
        target_balance = self._get_economy_balance(target_id)
        if target_balance < 1000:
            await interaction.response.send_message(
                f"❌ У {user.display_name} меньше 1000{self.currency_emoji}. Грабить нечего!",
                ephemeral=True
            )
            return
        
        robber_balance = self._get_economy_balance(robber_id)
        
        # Шанс успеха 40%
        success = random.random() < 0.40
        
        if success:
            # Успешное ограбление (10-30% баланса жертвы)
            stolen_percent = random.uniform(0.10, 0.30)
            stolen = int(target_balance * stolen_percent)
            
            self._update_economy_balance(robber_id, stolen)
            self._update_economy_balance(target_id, -stolen)
            
            em = EmbedBuilder.success(
                title="🔫 Ограбление Успешно!",
                description=f"Вы успешно ограбили {user.mention}!",
                user=interaction.user,
                fields=[
                    ("Украдено", f"{stolen:,}{self.currency_emoji}", True),
                    ("Ваш баланс", f"{robber_balance + stolen:,}{self.currency_emoji}", True)
                ]
            )
            
            # Логирование
            logs_cog = self.bot.get_cog('Logs')
            if logs_cog and interaction.guild:
                await logs_cog.log_admin_action(
                    guild=interaction.guild,
                    admin=interaction.user,
                    action="Ограбление",
                    target=user,
                    details=f"Украдено: {stolen:,}{self.currency_emoji}"
                )
        else:
            # Провал - штраф 20% своего баланса
            fine = int(robber_balance * 0.20)
            self._update_economy_balance(robber_id, -fine)
            
            em = EmbedBuilder.error(
                title="🚔 Ограбление Провалилось!",
                description="Полиция поймала вас!",
                user=interaction.user,
                fields=[
                    ("Штраф", f"-{fine:,}{self.currency_emoji}", True),
                    ("Ваш баланс", f"{robber_balance - fine:,}{self.currency_emoji}", True)
                ]
            )
        
        # Устанавливаем кулдаун
        self.rob_cooldowns[robber_id] = datetime.now()
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="crime", description="💰 Совершить преступление")
    @app_commands.describe(
        crime_type="Тип преступления"
    )
    @app_commands.choices(crime_type=[
        app_commands.Choice(name="🛍️ Мелкая кража (низкий риск, малая награда)", value="petty"),
        app_commands.Choice(name="🏠 Взлом (средний риск, средняя награда)", value="burglary"),
        app_commands.Choice(name="💼 Афера (высокий риск, большая награда)", value="heist")
    ])
    async def crime_commit(self, interaction: discord.Interaction, crime_type: str):
        """Совершить преступление"""
        user_id = str(interaction.user.id)
        
        # Проверка тюрьмы
        in_jail, time_left = self._is_in_jail(user_id)
        if in_jail:
            await interaction.response.send_message(f"🔒 Вы в тюрьме! Освобождение через: {time_left}", ephemeral=True)
            return
        
        # Параметры преступлений
        crimes = {
            "petty": {
                "name": "Мелкая кража",
                "success_rate": 0.70,
                "reward": (50, 200),
                "jail_time": 1  # часы
            },
            "burglary": {
                "name": "Взлом",
                "success_rate": 0.50,
                "reward": (300, 800),
                "jail_time": 3
            },
            "heist": {
                "name": "Афера",
                "success_rate": 0.30,
                "reward": (1000, 3000),
                "jail_time": 6
            }
        }
        
        crime_info = crimes[crime_type]
        success = random.random() < crime_info["success_rate"]
        
        if success:
            # Успех
            reward = random.randint(*crime_info["reward"])
            self._update_economy_balance(user_id, reward)
            
            em = EmbedBuilder.success(
                title=f"✅ {crime_info['name']} - Успех!",
                description="Вы успешно совершили преступление и скрылись!",
                user=interaction.user,
                fields=[
                    ("Награда", f"+{reward:,}{self.currency_emoji}", True)
                ]
            )
        else:
            # Провал - тюрьма
            jail_hours = crime_info["jail_time"]
            release_time = datetime.now() + timedelta(hours=jail_hours)
            self.jail_time[user_id] = release_time
            
            em = EmbedBuilder.error(
                title=f"🚔 {crime_info['name']} - Провал!",
                description="Вас поймала полиция!",
                user=interaction.user,
                fields=[
                    ("Тюрьма", f"{jail_hours} часов", True),
                    ("Освобождение", f"<t:{int(release_time.timestamp())}:R>", True)
                ]
            )
            em.set_footer(text="Используйте /bail для досрочного выхода")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="bail", description="💸 Выйти из тюрьмы досрочно")
    async def bail(self, interaction: discord.Interaction):
        """Заплатить залог для выхода из тюрьмы"""
        user_id = str(interaction.user.id)
        
        in_jail, time_left = self._is_in_jail(user_id)
        if not in_jail:
            await interaction.response.send_message("❌ Вы не в тюрьме!", ephemeral=True)
            return
        
        # Залог = 500 за каждый час
        release_time = self.jail_time[user_id]
        hours_left = (release_time - datetime.now()).total_seconds() / 3600
        bail_amount = int(hours_left * 500)
        
        balance = self._get_economy_balance(user_id)
        
        if balance < bail_amount:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"Залог: **{bail_amount:,}**{self.currency_emoji}\nУ вас: **{balance:,}**{self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Оплата залога
        self._update_economy_balance(user_id, -bail_amount)
        del self.jail_time[user_id]
        
        em = EmbedBuilder.success(
            title="🔓 Вы Свободны!",
            description="Залог оплачен, вы вышли из тюрьмы!",
            user=interaction.user,
            fields=[
                ("Оплачено", f"{bail_amount:,}{self.currency_emoji}", True)
            ]
        )
        
        await interaction.response.send_message(embed=em)


async def setup(bot):
    await bot.add_cog(Crime(bot))
