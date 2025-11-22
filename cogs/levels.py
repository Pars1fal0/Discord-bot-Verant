# levels.py
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta
import random
from typing import Optional
from utils.embed_builder import EmbedBuilder, Colors

class Levels(commands.Cog):
    """Система уровней и опыта с интеграцией в экономику"""
    
    def __init__(self, bot):
        self.bot = bot
        self.levels_file = 'levels.json'
        self._ensure_file()
        
        # Настройки XP
        self.xp_per_message = (15, 25)  # Мин и макс XP за сообщение
        self.message_cooldown = 30  # Секунды между начислениями XP за сообщения
        self.xp_per_reaction = 5  # XP за реакцию
        self.reaction_limit_per_hour = 10  # Максимум реакций в час
        self.voice_xp = 10  # XP за 5 минут в войсе
        self.voice_interval = 300  # Секунды (5 минут)
        self.dailyxp_amount = (200, 400)  # Диапазон ежедневного бонуса
        
        # Множитель для бустеров
        self.booster_multiplier = 1.2
    
    def _ensure_file(self):
        """Создание файла уровней если его нет"""
        if not os.path.exists(self.levels_file):
            with open(self.levels_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
    
    def _load_levels(self) -> dict:
        """Загрузка данных уровней"""
        with open(self.levels_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_levels(self, data: dict):
        """Сохранение данных уровней"""
        with open(self.levels_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def _get_user_data(self, user_id: str) -> dict:
        """Получение данных пользователя"""
        levels = self._load_levels()
        if user_id not in levels:
            levels[user_id] = {
                "xp": 0,
                "level": 1,
                "total_xp": 0,
                "messages_sent": 0,
                "last_xp_gain": None,
                "last_dailyxp": None,
                "last_reaction_xp": None,
                "voice_xp_last": None,
                "level_up_notifications": True,
                "reaction_count_hour": 0,
                "reaction_hour_start": None
            }
            self._save_levels(levels)
        return levels[user_id]
    
    def _xp_for_level(self, level: int) -> int:
        """Вычисляет необходимое количество XP для следующего уровня"""
        return 5 * (level ** 2) + 50 * level + 100
    
    def _get_booster_multiplier(self, member: discord.Member) -> float:
        """Получить множитель для бустера сервера"""
        if member.premium_since:
            return self.booster_multiplier
        return 1.0
    
    def _check_cooldown(self, last_time: Optional[str], seconds: int) -> tuple[bool, Optional[str]]:
        """Проверка кулдауна. Возвращает (доступно, время до доступности)"""
        if last_time is None:
            return True, None
        
        last_dt = datetime.fromisoformat(last_time)
        now = datetime.now()
        cooldown = timedelta(seconds=seconds)
        time_passed = now - last_dt
        
        if time_passed >= cooldown:
            return True, None
        
        time_left = cooldown - time_passed
        hours_left = int(time_left.total_seconds() // 3600)
        minutes_left = int((time_left.total_seconds() % 3600) // 60)
        seconds_left = int(time_left.total_seconds() % 60)
        
        if hours_left > 0:
            return False, f"{hours_left}ч {minutes_left}м"
        elif minutes_left > 0:
            return False, f"{minutes_left}м {seconds_left}с"
        else:
            return False, f"{seconds_left}с"
    
    async def _add_xp(self, user_id: str, member: discord.Member, amount: int) -> Optional[int]:
        """
        Добавляет XP пользователю и проверяет повышение уровня.
        Возвращает новый уровень если был levelup, иначе None
        """
        levels_data = self._load_levels()
        if user_id not in levels_data:
            self._get_user_data(user_id)
            levels_data = self._load_levels()
        
        user_data = levels_data[user_id]
        
        # Применяем множитель бустера
        multiplier = self._get_booster_multiplier(member)
        amount = int(amount * multiplier)
        
        user_data["xp"] += amount
        user_data["total_xp"] += amount
        
        # Проверяем повышение уровня
        xp_needed = self._xp_for_level(user_data["level"])
        new_level = None
        
        while user_data["xp"] >= xp_needed:
            user_data["xp"] -= xp_needed
            user_data["level"] += 1
            new_level = user_data["level"]
            xp_needed = self._xp_for_level(user_data["level"])
        
        self._save_levels(levels_data)
        return new_level
    
    async def _handle_levelup(self, member: discord.Member, new_level: int, channel: discord.TextChannel):
        """Обрабатывает повышение уровня: выдает награды и отправляет уведомление"""
        user_id = str(member.id)
        user_data = self._get_user_data(user_id)
        
        # Получаем ког экономики для выдачи награды
        economy_cog = self.bot.get_cog('Economy')
        reward = 0
        
        if economy_cog:
            booster_mult = 1.3 if member.premium_since else 1.0
            reward = economy_cog.reward_level_up(user_id, new_level, booster_mult)
        
        # Проверяем достижения за milestone уровни
        level_achievements = {
            10: ("level_10", "Новичок", 500),
            25: ("level_25", "Активист", 1000),
            50: ("level_50", "Ветеран", 2500),
            75: ("level_75", "Легенда", 5000),
            100: ("level_100", "Бессмертный", 10000)
        }
        
        achievement_reward = 0
        achievement_name = None
        
        if new_level in level_achievements and economy_cog:
            ach_id, ach_name, ach_reward = level_achievements[new_level]
            if economy_cog._check_achievement(user_id, ach_id):
                achievement_reward = ach_reward
                achievement_name = ach_name
                economy_cog._update_balance(user_id, ach_reward)
                economy_cog._add_transaction(user_id, "achievement", ach_reward, f"Достижение: {ach_name}")
        
        # Отправляем уведомление если включено
        if user_data.get("level_up_notifications", True):
            fields = []
            
            if reward > 0:
                fields.append(("💎 Награда", f"+{reward:,} крионов", True))
            
            if achievement_reward > 0:
                fields.append((f"🏆 Достижение: {achievement_name}", f"+{achievement_reward:,} крионов", True))
            
            xp_needed = self._xp_for_level(new_level)
            fields.append(("📊 Следующий уровень", f"{user_data['xp']}/{xp_needed} XP", False))
            
            em = EmbedBuilder.level(
                title="Новый уровень!",
                description=f"**{member.display_name}** достиг **{new_level} уровня**!",
                user=member,
                fields=fields
            )
            
            try:
                await channel.send(embed=em)
            except:
                pass
        
        # Логирование события
        logs_cog = self.bot.get_cog('Logs')
        if logs_cog and channel.guild:
            await logs_cog.log_level_up(
                guild=channel.guild,
                user=member,
                new_level=new_level,
                reward=reward + achievement_reward
            )
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Начисление XP за сообщения"""
        # Игнорируем ботов и DM
        if message.author.bot or not message.guild:
            return
        
        user_id = str(message.author.id)
        user_data = self._get_user_data(user_id)
        
        # Проверяем кулдаун
        can_gain, _ = self._check_cooldown(user_data.get("last_xp_gain"), self.message_cooldown)
        if not can_gain:
            return
        
        # Начисляем XP
        xp_amount = random.randint(*self.xp_per_message)
        new_level = await self._add_xp(user_id, message.author, xp_amount)
        
        # Обновляем время последнего получения XP и счетчик сообщений
        levels_data = self._load_levels()
        levels_data[user_id]["last_xp_gain"] = datetime.now().isoformat()
        levels_data[user_id]["messages_sent"] = levels_data[user_id].get("messages_sent", 0) + 1
        self._save_levels(levels_data)
        
        # Если был levelup, обрабатываем его
        if new_level:
            await self._handle_levelup(message.author, new_level, message.channel)
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Начисление XP за реакции"""
        # Игнорируем ботов
        if user.bot or not reaction.message.guild:
            return
        
        member = reaction.message.guild.get_member(user.id)
        if not member:
            return
        
        user_id = str(user.id)
        user_data = self._get_user_data(user_id)
        
        # Проверяем лимит реакций в час
        now = datetime.now()
        reaction_hour_start = user_data.get("reaction_hour_start")
        
        if reaction_hour_start:
            start_dt = datetime.fromisoformat(reaction_hour_start)
            if (now - start_dt).total_seconds() >= 3600:
                # Прошел час, сбрасываем счетчик
                user_data["reaction_count_hour"] = 0
                user_data["reaction_hour_start"] = now.isoformat()
        else:
            user_data["reaction_hour_start"] = now.isoformat()
            user_data["reaction_count_hour"] = 0
        
        # Проверяем не превышен ли лимит
        if user_data.get("reaction_count_hour", 0) >= self.reaction_limit_per_hour:
            return
        
        # Начисляем XP
        new_level = await self._add_xp(user_id, member, self.xp_per_reaction)
        
        # Обновляем счетчик реакций
        levels_data = self._load_levels()
        levels_data[user_id]["reaction_count_hour"] = levels_data[user_id].get("reaction_count_hour", 0) + 1
        self._save_levels(levels_data)
        
        # Если был levelup, обрабатываем его
        if new_level:
            await self._handle_levelup(member, new_level, reaction.message.channel)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Начисление XP за время в голосовых каналах"""
        # Игнорируем ботов
        if member.bot:
            return
        
        user_id = str(member.id)
        user_data = self._get_user_data(user_id)
        
        # Если пользователь зашел в канал
        if after.channel and not before.channel:
            # Записываем время входа
            levels_data = self._load_levels()
            levels_data[user_id]["voice_xp_last"] = datetime.now().isoformat()
            self._save_levels(levels_data)
        
        # Если пользователь в канале и прошло 5 минут
        elif after.channel and before.channel:
            last_voice_xp = user_data.get("voice_xp_last")
            if last_voice_xp:
                can_gain, _ = self._check_cooldown(last_voice_xp, self.voice_interval)
                if can_gain:
                    # Начисляем XP
                    new_level = await self._add_xp(user_id, member, self.voice_xp)
                    
                    # Обновляем время
                    levels_data = self._load_levels()
                    levels_data[user_id]["voice_xp_last"] = datetime.now().isoformat()
                    self._save_levels(levels_data)
                    
                    # Если был levelup, обрабатываем его
                    if new_level and after.channel:
                        # Находим текстовый канал для уведомления
                        text_channel = None
                        if after.channel.guild.system_channel:
                            text_channel = after.channel.guild.system_channel
                        else:
                            # Ищем первый доступный текстовый канал
                            for channel in after.channel.guild.text_channels:
                                if channel.permissions_for(after.channel.guild.me).send_messages:
                                    text_channel = channel
                                    break
                        
                        if text_channel:
                            await self._handle_levelup(member, new_level, text_channel)
        
        # Если пользователь вышел из канала, очищаем таймер
        elif not after.channel and before.channel:
            levels_data = self._load_levels()
            levels_data[user_id]["voice_xp_last"] = None
            self._save_levels(levels_data)
    
    # ==================== КОМАНДЫ ====================
    
    @app_commands.command(name="level", description="📊 Посмотреть свой уровень и прогресс")
    @app_commands.describe(user="Пользователь для проверки уровня")
    async def level(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Показать уровень пользователя"""
        target = user or interaction.user
        user_data = self._get_user_data(str(target.id))
        
        current_level = user_data["level"]
        current_xp = user_data["xp"]
        total_xp = user_data["total_xp"]
        messages = user_data.get("messages_sent", 0)
        
        xp_needed = self._xp_for_level(current_level)
        progress = (current_xp / xp_needed) * 100
        
        # Создаем прогресс-бар
        bar_length = 15
        filled = int((current_xp / xp_needed) * bar_length)
        bar = "▓" * filled + "░" * (bar_length - filled)
        
        # Ранг на сервере
        levels_data = self._load_levels()
        sorted_users = sorted(
            [(uid, data) for uid, data in levels_data.items()],
            key=lambda x: (x[1]["level"], x[1]["total_xp"]),
            reverse=True
        )
        rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == str(target.id)), 0)
        
        em = discord.Embed(
            title=f"📊 Уровень {target.display_name}",
            color=discord.Color.blue()
        )
        em.set_thumbnail(url=target.display_avatar.url)
        
        em.add_field(
            name="Уровень",
            value=f"**{current_level}**",
            inline=True
        )
        em.add_field(
            name="Ранг",
            value=f"**#{rank}**",
            inline=True
        )
        em.add_field(
            name="Сообщений",
            value=f"**{messages:,}**",
            inline=True
        )
        
        em.add_field(
            name="Прогресс до следующего уровня",
            value=f"{bar}\n{current_xp:,}/{xp_needed:,} XP ({progress:.1f}%)",
            inline=False
        )
        
        em.add_field(
            name="Всего опыта",
            value=f"{total_xp:,} XP",
            inline=True
        )
        
        # Награда за следующий уровень
        next_reward = (current_level + 1) * 50
        if (current_level + 1) % 10 == 0:
            next_reward += 200
        
        fields = [
            ("Уровень", f"**{current_level}**", True),
            ("Ранг", f"**#{rank}**", True),
            ("Сообщений", f"**{messages:,}**", True),
            ("Прогресс до следующего уровня", f"{bar}\n{current_xp:,}/{xp_needed:,} XP ({progress:.1f}%)", False),
            ("Всего опыта", f"{total_xp:,} XP", True),
            ("Награда за следующий уровень", f"💎 {next_reward:,} крионов", True)
        ]
        
        em = EmbedBuilder.level(
            title=f"Уровень {target.display_name}",
            description=f"Профиль пользователя",
            user=target,
            fields=fields,
            footer_text=f"Запрос от {interaction.user.display_name}"
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="rank", description="🏆 Топ пользователей по уровню")
    async def rank(self, interaction: discord.Interaction):
        """Показать топ-10 пользователей по уровню"""
        levels_data = self._load_levels()
        
        if not levels_data:
            await interaction.response.send_message("❌ Пока никто не набрал опыта!", ephemeral=True)
            return
        
        # Сортируем по уровню и общему XP
        sorted_users = sorted(
            levels_data.items(),
            key=lambda x: (x[1]["level"], x[1]["total_xp"]),
            reverse=True
        )[:10]
        
        em = discord.Embed(
            title="🏆 Топ по уровню",
            description="10 самых опытных участников сервера",
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, (user_id, data) in enumerate(sorted_users, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                medal = medals[idx - 1] if idx <= 3 else f"`{idx}.`"
                em.add_field(
                    name=f"{medal} {user.display_name}",
                    value=f"Уровень {data['level']} | {data['total_xp']:,} XP",
                    inline=False
                )
            except:
                continue
        
        em.set_footer(text=f"Запрос от {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="dailyxp", description="🎁 Получить ежедневный бонус опыта")
    async def dailyxp(self, interaction: discord.Interaction):
        """Ежедневный бонус XP"""
        user_id = str(interaction.user.id)
        user_data = self._get_user_data(user_id)
        
        can_claim, time_left = self._check_cooldown(user_data.get("last_dailyxp"), 24 * 3600)
        
        if not can_claim:
            em = discord.Embed(
                title="⏰ Слишком рано!",
                description=f"Вы уже получили ежедневный бонус XP!\nПопробуйте снова через: **{time_left}**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Начисляем XP
        xp_amount = random.randint(*self.dailyxp_amount)
        new_level = await self._add_xp(user_id, interaction.user, xp_amount)
        
        # Обновляем время
        levels_data = self._load_levels()
        levels_data[user_id]["last_dailyxp"] = datetime.now().isoformat()
        self._save_levels(levels_data)
        
        # Применяем множитель бустера для отображения
        multiplier = self._get_booster_multiplier(interaction.user)
        actual_xp = int(xp_amount * multiplier)
        
        em = discord.Embed(
            title="🎁 Ежедневный бонус получен!",
            description=f"Вы получили **{actual_xp} XP**!",
            color=discord.Color.green()
        )
        
        if multiplier > 1.0:
            em.add_field(
                name="🚀 Бонус бустера!",
                value=f"Множитель x{multiplier} ({xp_amount} → {actual_xp} XP)",
                inline=False
            )
        
        user_data = self._get_user_data(user_id)
        em.add_field(
            name="Текущий уровень",
            value=f"Уровень {user_data['level']} | {user_data['xp']}/{self._xp_for_level(user_data['level'])} XP",
            inline=False
        )
        
        em.set_footer(text="Возвращайтесь завтра за новым бонусом!")
        
        await interaction.response.send_message(embed=em)
        
        # Если был levelup, отправляем уведомление
        if new_level:
            await self._handle_levelup(interaction.user, new_level, interaction.channel)
    
    @app_commands.command(name="levelnotify", description="🔔 Включить/выключить уведомления о повышении уровня")
    async def levelnotify(self, interaction: discord.Interaction):
        """Переключить уведомления о levelup"""
        user_id = str(interaction.user.id)
        levels_data = self._load_levels()
        
        if user_id not in levels_data:
            self._get_user_data(user_id)
            levels_data = self._load_levels()
        
        current = levels_data[user_id].get("level_up_notifications", True)
        levels_data[user_id]["level_up_notifications"] = not current
        self._save_levels(levels_data)
        
        status = "включены" if not current else "выключены"
        emoji = "🔔" if not current else "🔕"
        
        em = discord.Embed(
            title=f"{emoji} Уведомления {status}",
            description=f"Уведомления о повышении уровня теперь **{status}**",
            color=discord.Color.green() if not current else discord.Color.red()
        )
        
        await interaction.response.send_message(embed=em, ephemeral=True)
    
    @app_commands.command(name="setxp", description="⚙️ Установить XP пользователю (только владелец)")
    @app_commands.describe(
        user="Пользователь",
        xp="Количество XP"
    )
    async def setxp(self, interaction: discord.Interaction, user: discord.Member, xp: int):
        """Установить XP пользователю (только владелец)"""
        # Проверка владельца через OWNER_ID из .env
        owner_id = os.getenv('OWNER_ID')
        if not owner_id:
            await interaction.response.send_message('❌ OWNER_ID не установлен в .env файле.', ephemeral=True)
            return
        
        try:
            owner_id = int(owner_id)
        except ValueError:
            await interaction.response.send_message('❌ OWNER_ID в .env должен быть числом.', ephemeral=True)
            return
        
        if interaction.user.id != owner_id:
            await interaction.response.send_message('❌ Эта команда доступна только владельцу бота.', ephemeral=True)
            return
        
        if xp < 0:
            await interaction.response.send_message("❌ XP не может быть отрицательным!", ephemeral=True)
            return
        
        user_id = str(user.id)
        levels_data = self._load_levels()
        
        if user_id not in levels_data:
            self._get_user_data(user_id)
            levels_data = self._load_levels()
        
        levels_data[user_id]["xp"] = xp
        levels_data[user_id]["total_xp"] = xp
        self._save_levels(levels_data)
        
        await interaction.response.send_message(
            f"✅ Установлено {xp} XP для {user.display_name}",
            ephemeral=True
        )
    
    @app_commands.command(name="setlevel", description="⚙️ Установить уровень пользователю (только владелец)")
    @app_commands.describe(
        user="Пользователь",
        level="Уровень"
    )
    async def setlevel(self, interaction: discord.Interaction, user: discord.Member, level: int):
        """Установить уровень пользователю (только владелец)"""
        # Проверка владельца через OWNER_ID из .env
        owner_id = os.getenv('OWNER_ID')
        if not owner_id:
            await interaction.response.send_message('❌ OWNER_ID не установлен в .env файле.', ephemeral=True)
            return
        
        try:
            owner_id = int(owner_id)
        except ValueError:
            await interaction.response.send_message('❌ OWNER_ID в .env должен быть числом.', ephemeral=True)
            return
        
        if interaction.user.id != owner_id:
            await interaction.response.send_message('❌ Эта команда доступна только владельцу бота.', ephemeral=True)
            return
        
        if level < 1:
            await interaction.response.send_message("❌ Уровень должен быть минимум 1!", ephemeral=True)
            return
        
        user_id = str(user.id)
        levels_data = self._load_levels()
        
        if user_id not in levels_data:
            self._get_user_data(user_id)
            levels_data = self._load_levels()
        
        levels_data[user_id]["level"] = level
        levels_data[user_id]["xp"] = 0
        self._save_levels(levels_data)
        
        await interaction.response.send_message(
            f"✅ Установлен {level} уровень для {user.display_name}",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Levels(bot))
