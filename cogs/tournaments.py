# tournaments.py - Турниры
"""Система турниров и соревнований"""
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime
from typing import Optional
from utils.embed_builder import EmbedBuilder, Colors


class Tournaments(commands.Cog):
    """Система турниров"""
    
    def __init__(self, bot):
        self.bot = bot
        self.tournaments_file = 'tournaments.json'
        self.currency_emoji = "💎"
        self._ensure_file()
    
    def _ensure_file(self):
        if not os.path.exists(self.tournaments_file):
            with open(self.tournaments_file, 'w', encoding='utf-8') as f:
                json.dump({"active": {}, "history": []}, f, ensure_ascii=False, indent=4)
    
    def _load_tournaments(self):
        with open(self.tournaments_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_tournaments(self, data):
        with open(self.tournaments_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def _get_economy_balance(self, user_id: str) -> int:
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            return economy_cog._get_user_data(user_id).get('balance', 0)
        return 0
    
    def _update_economy_balance(self, user_id: str, amount: int):
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            economy_cog._update_balance(user_id, amount)
            economy_cog._add_transaction(user_id, "tournament", amount, "Турнир")
    
    @app_commands.command(name="tournament-create", description="🏆 [ADMIN] Создать турнир")
    @app_commands.describe(
        name="Название турнира",
        entry_fee="Входная плата",
        max_participants="Максимум участников"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def tournament_create(
        self, 
        interaction: discord.Interaction, 
        name: str,
        entry_fee: int,
        max_participants: int = 16
    ):
        """Создать новый турнир"""
        if entry_fee < 0:
            await interaction.response.send_message("❌ Входная плата не может быть отрицательной!", ephemeral=True)
            return
        
        if max_participants < 2 or max_participants > 32:
            await interaction.response.send_message("❌ Участников должно быть от 2 до 32!", ephemeral=True)
            return
        
        tournaments = self._load_tournaments()
        guild_id = str(interaction.guild.id)
        
        if guild_id in tournaments["active"]:
            await interaction.response.send_message("❌ На сервере уже есть активный турнир!", ephemeral=True)
            return
        
        # Создаём турнир
        tournaments["active"][guild_id] = {
            "name": name,
            "creator": str(interaction.user.id),
            "entry_fee": entry_fee,
            "max_participants": max_participants,
            "participants": [],
            "prize_pool": 0,
            "created_at": datetime.now().isoformat()
        }
        
        self._save_tournaments(tournaments)
        
        em = EmbedBuilder.success(
            title="🏆 Турнир Создан!",
            description=f"**{name}**",
            user=interaction.user,
            fields=[
                ("Входная плата", f"{entry_fee:,}{self.currency_emoji}", True),
                ("Макс. участников", str(max_participants), True),
                ("Призовой фонд", f"{entry_fee * max_participants:,}{self.currency_emoji}", False)
            ]
        )
        em.set_footer(text="Используйте /tournament-join для участия")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="tournament-join", description="🎫 Присоединиться к турниру")
    async def tournament_join(self, interaction: discord.Interaction):
        """Присоединиться к активному турниру"""
        tournaments = self._load_tournaments()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in tournaments["active"]:
            await interaction.response.send_message("❌ Нет активных турниров!", ephemeral=True)
            return
        
        tournament = tournaments["active"][guild_id]
        user_id = str(interaction.user.id)
        
        # Проверки
        if user_id in tournament["participants"]:
            await interaction.response.send_message("❌ Вы уже участвуете в турнире!", ephemeral=True)
            return
        
        if len(tournament["participants"]) >= tournament["max_participants"]:
            await interaction.response.send_message("❌ Турнир заполнен!", ephemeral=True)
            return
        
        # Проверка баланса
        entry_fee = tournament["entry_fee"]
        balance = self._get_economy_balance(user_id)
        
        if balance < entry_fee:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"Входная плата: **{entry_fee:,}**{self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Регистрация
        self._update_economy_balance(user_id, -entry_fee)
        tournament["participants"].append(user_id)
        tournament["prize_pool"] += entry_fee
        
        self._save_tournaments(tournaments)
        
        em = EmbedBuilder.success(
            title="✅ Вы в турнире!",
            description=f"Вы присоединились к **{tournament['name']}**!",
            user=interaction.user,
            fields=[
                ("Участников", f"{len(tournament['participants'])}/{tournament['max_participants']}", True),
                ("Призовой фонд", f"{tournament['prize_pool']:,}{self.currency_emoji}", True)
            ]
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="tournament-status", description="📊 Статус турнира")
    async def tournament_status(self, interaction: discord.Interaction):
        """Показать статус турнира"""
        tournaments = self._load_tournaments()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in tournaments["active"]:
            em = EmbedBuilder.info(
                title="📊 Статус Турнира",
                description="Нет активных турниров на этом сервере",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em)
            return
        
        tournament = tournaments["active"][guild_id]
        
        # Список участников
        participants_list = []
        for i, uid in enumerate(tournament["participants"][:10], 1):
            try:
                user = await self.bot.fetch_user(int(uid))
                participants_list.append(f"{i}. {user.display_name}")
            except:
                pass
        
        if len(tournament["participants"]) > 10:
            participants_list.append(f"... и ещё {len(tournament['participants']) - 10}")
        
        participants_text = "\n".join(participants_list) if participants_list else "Пока нет участников"
        
        em = EmbedBuilder.info(
            title=f"🏆 {tournament['name']}",
            description="Статус активного турнира",
            user=interaction.user,
            fields=[
                ("Участников", f"{len(tournament['participants'])}/{tournament['max_participants']}", True),
                ("Входная плата", f"{tournament['entry_fee']:,}{self.currency_emoji}", True),
                ("Призовой фонд", f"{tournament['prize_pool']:,}{self.currency_emoji}", False),
                ("Участники", participants_text, False)
            ]
        )
        em.set_footer(text="Используйте /tournament-join для участия")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="tournament-start", description="🎮 [ADMIN] Запустить турнир")
    @app_commands.checks.has_permissions(administrator=True)
    async def tournament_start(self, interaction: discord.Interaction):
        """Запустить и завершить турнир"""
        tournaments = self._load_tournaments()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in tournaments["active"]:
            await interaction.response.send_message("❌ Нет активных турниров!", ephemeral=True)
            return
        
        tournament = tournaments["active"][guild_id]
        
        if len(tournament["participants"]) < 2:
            await interaction.response.send_message("❌ Минимум 2 участника!", ephemeral=True)
            return
        
        # Определяем победителей (топ-3)
        import random
        participants = tournament["participants"].copy()
        random.shuffle(participants)
        
        prize_pool = tournament["prize_pool"]
        
        # Распределение призов: 50%, 30%, 20%
        if len(participants) >= 3:
            first_prize = int(prize_pool * 0.50)
            second_prize = int(prize_pool * 0.30)
            third_prize = int(prize_pool * 0.20)
            
            winners = [
                (participants[0], first_prize, "🥇"),
                (participants[1], second_prize, "🥈"),
                (participants[2], third_prize, "🥉")
            ]
        elif len(participants) == 2:
            first_prize = int(prize_pool * 0.70)
            second_prize = int(prize_pool * 0.30)
            winners = [
                (participants[0], first_prize, "🥇"),
                (participants[1], second_prize, "🥈")
            ]
        else:
            winners = [(participants[0], prize_pool, "🥇")]
        
        # Выплачиваем призы
        for user_id, prize, medal in winners:
            self._update_economy_balance(user_id, prize)
        
        # Формируем результаты
        results_text = ""
        for i, (user_id, prize, medal) in enumerate(winners, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                results_text += f"{medal} **{user.display_name}** - {prize:,}{self.currency_emoji}\n"
            except:
                pass
        
        # Сохраняем в историю
        tournament["finished_at"] = datetime.now().isoformat()
        tournament["winners"] = [(uid, prize) for uid, prize, _ in winners]
        tournaments["history"].append(tournament)
        
        # Удаляем активный турнир
        del tournaments["active"][guild_id]
        
        self._save_tournaments(tournaments)
        
        em = discord.Embed(
            title=f"🏆 Турнир {tournament['name']} Завершён!",
            description="**Победители:**\n" + results_text,
            color=Colors.PREMIUM,
            timestamp=discord.utils.utcnow()
        )
        em.add_field(name="Участников", value=str(len(tournament["participants"])), inline=True)
        em.add_field(name="Призовой фонд", value=f"{prize_pool:,}{self.currency_emoji}", inline=True)
        em.set_footer(text="Поздравляем победителей!")
        
        await interaction.response.send_message(embed=em)


async def setup(bot):
    await bot.add_cog(Tournaments(bot))
