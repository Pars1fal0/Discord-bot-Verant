# enhancements.py - Престиж, Бустеры, Квесты, Титулы
"""Дополнительные системы прогрессии"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Literal
from utils.embed_builder import EmbedBuilder, Colors


class Enhancements(commands.Cog):
    """Улучшения и прогрессия"""
    
    def __init__(self, bot):
        self.bot = bot
        self.enhancements_file = 'enhancements.json'
        self.currency_emoji = "💎"
        self._ensure_file()
        self.check_quests.start()
    
    def _ensure_file(self):
        if not os.path.exists(self.enhancements_file):
            data = {
                "prestiges": {},  # user_id: prestige_level
                "boosters": {},  # user_id: {type: expiry_time}
                "quests": {},  # user_id: {quest_id: progress}
                "titles": {}  # user_id: [title_ids]
            }
            with open(self.enhancements_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
    
    def _load_data(self):
        with open(self.enhancements_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_data(self, data):
        with open(self.enhancements_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def _get_user_level(self, user_id: str) -> int:
        levels_cog = self.bot.get_cog('Levels')
        if levels_cog:
            return levels_cog._get_user_data(user_id).get('level', 1)
        return 1
    
    def _get_economy_balance(self, user_id: str) -> int:
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            return economy_cog._get_user_data(user_id).get('balance', 0)
        return 0
    
    def _update_economy_balance(self, user_id: str, amount: int):
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            economy_cog._update_balance(user_id, amount)
    
    # ==================== ПРЕСТИЖ ====================
    
    @app_commands.command(name="prestige", description="⭐ Престиж (сброс уровня с бонусами)")
    async def prestige(self, interaction: discord.Interaction):
        """Престиж - сброс уровня с постоянными бонусами"""
        user_id = str(interaction.user.id)
        level = self._get_user_level(user_id)
        
        # Требуется 50+ уровень
        if level < 50:
            em = EmbedBuilder.error(
                title="Недостаточный уровень!",
                description=f"Для престижа нужен **50** уровень\nУ вас: **{level}** уровень",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        data = self._load_data()
        current_prestige = data["prestiges"].get(user_id, 0)
        new_prestige = current_prestige + 1
        
        # Бонусы престижа (за каждый престиж +10% к XP и деньгам)
        xp_bonus = new_prestige * 10
        money_bonus = new_prestige * 10
        
        # Сбрасываем уровень через levels cog
        levels_cog = self.bot.get_cog('Levels')
        if levels_cog:
            levels_data = levels_cog._load_levels()
            if user_id in levels_data:
                levels_data[user_id]["level"] = 1
                levels_data[user_id]["xp"] = 0
                levels_cog._save_levels(levels_data)
        
        # Сохраняем престиж
        data["prestiges"][user_id] = new_prestige
        self._save_data(data)
        
        # Даём титул
        if "titles" not in data:
            data["titles"] = {}
        if user_id not in data["titles"]:
            data["titles"][user_id] = []
        
        prestige_title = f"prestige_{new_prestige}"
        if prestige_title not in data["titles"][user_id]:
            data["titles"][user_id].append(prestige_title)
            self._save_data(data)
        
        em = EmbedBuilder.success(
            title="⭐ Престиж Достигнут!",
            description=f"Поздравляем с **{new_prestige}** престижем!",
            user=interaction.user,
            fields=[
                ("Новый уровень", "1", True),
                ("Престиж", f"⭐ {new_prestige}", True),
                ("Бонус XP", f"+{xp_bonus}%", True),
                ("Бонус денег", f"+{money_bonus}%", True),
                ("Новый титул", f"Престиж {new_prestige}", False)
            ]
        )
        em.set_footer(text="Ваш прогресс сброшен, но бонусы постоянны!")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="prestige-status", description="📊 Проверить престиж")
    @app_commands.describe(user="Пользователь (по умолчанию - вы)")
    async def prestige_status(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Показать престиж пользователя"""
        target = user or interaction.user
        user_id = str(target.id)
        
        data = self._load_data()
        prestige = data["prestiges"].get(user_id, 0)
        level = self._get_user_level(user_id)
        
        xp_bonus = prestige * 10
        money_bonus = prestige * 10
        
        em = EmbedBuilder.info(
            title=f"⭐ Престиж - {target.display_name}",
            description=f"Престиж: **{prestige}**" if prestige > 0 else "Нет престижа",
            user=target,
            fields=[
                ("Текущий уровень", str(level), True),
                ("Престиж", f"⭐ {prestige}", True),
                ("Бонус XP", f"+{xp_bonus}%" if prestige > 0 else "—", True),
                ("Бонус денег", f"+{money_bonus}%" if prestige > 0 else "—", True)
            ]
        )
        
        if prestige == 0:
            em.set_footer(text="Достигните 50 уровня для первого престижа")
        
        await interaction.response.send_message(embed=em)
    
    # ==================== БУСТЕРЫ ====================
    
    @app_commands.command(name="booster-buy", description="🚀 Купить бустер")
    @app_commands.describe(
        booster_type="Тип бустера",
        duration="Длительность (часы)"
    )
    @app_commands.choices(booster_type=[
        app_commands.Choice(name="💎 Бустер денег (x2)", value="money"),
        app_commands.Choice(name="⭐ Бустер XP (x2)", value="xp"),
        app_commands.Choice(name="🎰 Бустер удачи (+20%)", value="luck")
    ])
    async def booster_buy(
        self, 
        interaction: discord.Interaction, 
        booster_type: str,
        duration: int
    ):
        """Купить бустер"""
        if duration < 1 or duration > 24:
            await interaction.response.send_message("❌ Длительность от 1 до 24 часов!", ephemeral=True)
            return
        
        # Стоимость: 1000 за час
        cost = duration * 1000
        user_id = str(interaction.user.id)
        balance = self._get_economy_balance(user_id)
        
        if balance < cost:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"Нужно: **{cost:,}**{self.currency_emoji}\nУ вас: **{balance:,}**{self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Покупка
        self._update_economy_balance(user_id, -cost)
        
        data = self._load_data()
        if user_id not in data["boosters"]:
            data["boosters"][user_id] = {}
        
        expiry = datetime.now() + timedelta(hours=duration)
        data["boosters"][user_id][booster_type] = expiry.isoformat()
        self._save_data(data)
        
        booster_names = {
            "money": "💎 Бустер денег",
            "xp": "⭐ Бустер XP",
            "luck": "🎰 Бустер удачи"
        }
        
        em = EmbedBuilder.success(
            title="🚀 Бустер Активирован!",
            description=f"**{booster_names[booster_type]}**",
            user=interaction.user,
            fields=[
                ("Длительность", f"{duration}ч", True),
                ("Стоимость", f"{cost:,}{self.currency_emoji}", True),
                ("Истекает", f"<t:{int(expiry.timestamp())}:R>", False)
            ]
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="booster-status", description="📊 Активные бустеры")
    async def booster_status(self, interaction: discord.Interaction):
        """Показать активные бустеры"""
        user_id = str(interaction.user.id)
        data = self._load_data()
        
        if user_id not in data["boosters"] or not data["boosters"][user_id]:
            em = EmbedBuilder.info(
                title="📊 Активные Бустеры",
                description="У вас нет активных бустеров",
                user=interaction.user
            )
            em.set_footer(text="Используйте /booster-buy для покупки")
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        booster_names = {
            "money": "💎 Бустер денег (x2)",
            "xp": "⭐ Бустер XP (x2)",
            "luck": "🎰 Бустер удачи (+20%)"
        }
        
        fields = []
        active_count = 0
        
        for btype, expiry_str in data["boosters"][user_id].items():
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.now() < expiry:
                active_count += 1
                time_left = expiry - datetime.now()
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                fields.append((
                    booster_names.get(btype, btype),
                    f"Осталось: {hours}ч {minutes}м",
                    False
                ))
        
        if active_count == 0:
            em = EmbedBuilder.info(
                title="📊 Активные Бустеры",
                description="Все бустеры истекли",
                user=interaction.user
            )
        else:
            em = EmbedBuilder.info(
                title="📊 Активные Бустеры",
                description=f"Активно: **{active_count}**",
                user=interaction.user,
                fields=fields
            )
        
        await interaction.response.send_message(embed=em, ephemeral=True)
    
    # ==================== КВЕСТЫ ====================
    
    @tasks.loop(hours=24)
    async def check_quests(self):
        """Обновление ежедневных квестов"""
        pass
    
    @check_quests.before_loop
    async def before_check_quests(self):
        await self.bot.wait_until_ready()
    
    @app_commands.command(name="quests", description="📜 Доступные квесты")
    async def quests_list(self, interaction: discord.Interaction):
        """Показать доступные квесты"""
        # Простые ежедневные квесты
        daily_quests = [
            {"id": "earn_1000", "name": "Заработать 1000💎", "reward": 500, "type": "earn"},
            {"id": "win_games", "name": "Выиграть 3 игры", "reward": 300, "type": "games"},
            {"id": "send_messages", "name": "Отправить 50 сообщений", "reward": 200, "type": "messages"}
        ]
        
        user_id = str(interaction.user.id)
        data = self._load_data()
        
        if user_id not in data["quests"]:
            data["quests"][user_id] = {}
        
        fields = []
        for quest in daily_quests:
            progress = data["quests"][user_id].get(quest["id"], 0)
            status = "✅ Выполнено" if progress >= 100 else f"⏳ {progress}%"
            fields.append((
                quest["name"],
                f"Награда: {quest['reward']}💎\nСтатус: {status}",
                True
            ))
        
        em = EmbedBuilder.info(
            title="📜 Ежедневные Квесты",
            description="Выполняйте квесты для получения наград!",
            user=interaction.user,
            fields=fields
        )
        em.set_footer(text="Квесты обновляются каждые 24 часа")
        
        await interaction.response.send_message(embed=em)
    
    # ==================== ТИТУЛЫ ====================
    
    @app_commands.command(name="titles", description="🏅 Ваши титулы")
    async def titles_list(self, interaction: discord.Interaction):
        """Показать титулы пользователя"""
        user_id = str(interaction.user.id)
        data = self._load_data()
        
        if user_id not in data.get("titles", {}) or not data["titles"][user_id]:
            em = EmbedBuilder.info(
                title="🏅 Ваши Титулы",
                description="У вас пока нет титулов.\nПолучайте титулы за достижения!",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        title_names = {
            "prestige_1": "⭐ Престиж I",
            "prestige_2": "⭐⭐ Престиж II",
            "prestige_3": "⭐⭐⭐ Престиж III",
            "rich": "💎 Богач",
            "gambler": "🎰 Азартный",
            "trader": "📈 Трейдер",
            "business_tycoon": "🏢 Магнат"
        }
        
        titles_text = "\n".join([
            title_names.get(title, title) 
            for title in data["titles"][user_id]
        ])
        
        em = EmbedBuilder.info(
            title="🏅 Ваши Титулы",
            description=titles_text,
            user=interaction.user
        )
        em.set_footer(text=f"Всего титулов: {len(data['titles'][user_id])}")
        
        await interaction.response.send_message(embed=em, ephemeral=True)
    
    @app_commands.command(name="grant-title", description="🏅 [ADMIN] Выдать титул")
    @app_commands.describe(
        user="Пользователь",
        title="Название титула"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def grant_title(self, interaction: discord.Interaction, user: discord.Member, title: str):
        """Выдать титул пользователю"""
        user_id = str(user.id)
        data = self._load_data()
        
        if "titles" not in data:
            data["titles"] = {}
        
        if user_id not in data["titles"]:
            data["titles"][user_id] = []
        
        if title in data["titles"][user_id]:
            await interaction.response.send_message(f"❌ У {user.display_name} уже есть этот титул!", ephemeral=True)
            return
        
        data["titles"][user_id].append(title)
        self._save_data(data)
        
        em = EmbedBuilder.success(
            title="🏅 Титул Выдан!",
            description=f"{user.mention} получил титул **{title}**!",
            user=interaction.user
        )
        
        await interaction.response.send_message(embed=em)


async def setup(bot):
    await bot.add_cog(Enhancements(bot))
