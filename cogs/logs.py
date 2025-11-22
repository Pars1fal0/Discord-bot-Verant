# logs.py
"""Система логирования событий на сервере"""
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime
from typing import Optional
from utils.embed_builder import EmbedBuilder, Colors


class Logs(commands.Cog):
    """Ког для системы логирования"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = 'logs_config.json'
        self.logs_data_file = 'logs_data.json'
        self._ensure_config()
        self._ensure_logs_data()
    
    def _ensure_config(self):
        """Создание файла конфигурации если его нет"""
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
    
    def _ensure_logs_data(self):
        """Создание файла данных логов"""
        if not os.path.exists(self.logs_data_file):
            with open(self.logs_data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
    
    def _load_logs_data(self) -> dict:
        """Загрузка данных логов"""
        with open(self.logs_data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_logs_data(self, data: dict):
        """Сохранение данных логов"""
        with open(self.logs_data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def _store_log(self, guild_id: int, event_type: str, data: dict):
        """Сохранить лог в файл"""
        logs = self._load_logs_data()
        guild_str = str(guild_id)
        
        if guild_str not in logs:
            logs[guild_str] = []
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        
        logs[guild_str].append(log_entry)
        
        # Ограничиваем размер (храним последние 1000 событий)
        if len(logs[guild_str]) > 1000:
            logs[guild_str] = logs[guild_str][-1000:]
        
        self._save_logs_data(logs)
    
    def _load_config(self) -> dict:
        """Загрузка конфигурации логов"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_config(self, data: dict):
        """Сохранение конфигурации логов"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def _get_log_channel(self, guild_id: int) -> Optional[int]:
        """Получить ID канала логов для гильдии"""
        config = self._load_config()
        guild_config = config.get(str(guild_id), {})
        return guild_config.get('log_channel')
    
    def _set_log_channel(self, guild_id: int, channel_id: int):
        """Установить канал логов для гильдии"""
        config = self._load_config()
        if str(guild_id) not in config:
            config[str(guild_id)] = {}
        config[str(guild_id)]['log_channel'] = channel_id
        config[str(guild_id)]['enabled'] = True
        self._save_config(config)
    
    def _disable_logs(self, guild_id: int):
        """Отключить логи для гильдии"""
        config = self._load_config()
        if str(guild_id) in config:
            config[str(guild_id)]['enabled'] = False
            self._save_config(config)
    
    def _is_enabled(self, guild_id: int) -> bool:
        """Проверить включены ли логи для гильдии"""
        config = self._load_config()
        guild_config = config.get(str(guild_id), {})
        return guild_config.get('enabled', False)
    
    async def log_event(
        self,
        guild: discord.Guild,
        title: str,
        description: str,
        color: int,
        fields: list = None,
        user: discord.User = None
    ):
        """
        Отправить событие в канал логов
        
        Args:
            guild: Гильдия
            title: Заголовок события
            description: Описание
            color: Цвет embed
            fields: Дополнительные поля [(name, value, inline), ...]
            user: Пользователь связанный с событием
        """
        if not self._is_enabled(guild.id):
            return
        
        channel_id = self._get_log_channel(guild.id)
        if not channel_id:
            return
        
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return
        
        # Проверяем права на отправку сообщений
        if not channel.permissions_for(guild.me).send_messages:
            return
        
        em = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        
        if user:
            em.set_thumbnail(url=user.display_avatar.url)
        
        if fields:
            for name, value, inline in fields:
                em.add_field(name=name, value=value, inline=inline)
        
        em.set_footer(text=f"Сервер: {guild.name}", icon_url=guild.icon.url if guild.icon else None)
        
        try:
            await channel.send(embed=em)
        except discord.Forbidden:
            pass
        except Exception:
            pass
    
    # Методы для логирования конкретных событий
    
    async def log_economy_transaction(
        self,
        guild: discord.Guild,
        user: discord.User,
        transaction_type: str,
        amount: int,
        details: str = ""
    ):
        """Логировать экономическую транзакцию"""
        # Сохраняем в файл
        self._store_log(guild.id, "economy", {
            "user_id": str(user.id),
            "user_name": user.display_name,
            "transaction_type": transaction_type,
            "amount": amount,
            "details": details
        })
        
        # Отправляем в канал
        await self.log_event(
            guild=guild,
            title="💰 Экономическая Транзакция",
            description=f"**Тип:** {transaction_type}\n**Сумма:** {amount:,} 💎",
            color=Colors.ECONOMY,
            fields=[
                ("Пользователь", user.mention, True),
                ("Детали", details or "—", False)
            ],
            user=user
        )
    
    async def log_level_up(
        self,
        guild: discord.Guild,
        user: discord.User,
        new_level: int,
        reward: int
    ):
        """Логировать повышение уровня"""
        await self.log_event(
            guild=guild,
            title="📊 Повышение Уровня",
            description=f"{user.mention} достиг **{new_level} уровня**!",
            color=Colors.LEVEL,
            fields=[
                ("Новый уровень", str(new_level), True),
                ("Награда", f"{reward:,} 💎", True)
            ],
            user=user
        )
    
    async def log_game_result(
        self,
        guild: discord.Guild,
        user: discord.User,
        game_name: str,
        is_win: bool,
        bet: int,
        result: int
    ):
        """Логировать результат игры"""
        result_text = "Выигрыш" if is_win else "Проигрыш"
        color = Colors.GAME_WIN if is_win else Colors.GAME_LOSS
        
        await self.log_event(
            guild=guild,
            title=f"🎮 Игра: {game_name}",
            description=f"**Результат:** {result_text}",
            color=color,
            fields=[
                ("Игрок", user.mention, True),
                ("Ставка", f"{bet:,} 💎", True),
                ("Изменение", f"{result:+,} 💎", True)
            ],
            user=user
        )
    
    async def log_admin_action(
        self,
        guild: discord.Guild,
        admin: discord.User,
        action: str,
        target: Optional[discord.User] = None,
        details: str = ""
    ):
        """Логировать административное действие"""
        description = f"**Действие:** {action}"
        if target:
            description += f"\n**Цель:** {target.mention}"
        
        fields = [("Администратор", admin.mention, True)]
        if details:
            fields.append(("Детали", details, False))
        
        await self.log_event(
            guild=guild,
            title="⚙️ Административное Действие",
            description=description,
            color=Colors.PRIMARY,
            fields=fields,
            user=admin
        )
    
    async def log_achievement(
        self,
        guild: discord.Guild,
        user: discord.User,
        achievement_name: str,
        reward: int
    ):
        """Логировать получение достижения"""
        await self.log_event(
            guild=guild,
            title="🏆 Достижение Разблокировано",
            description=f"{user.mention} получил достижение **{achievement_name}**!",
            color=Colors.PREMIUM,
            fields=[
                ("Достижение", achievement_name, True),
                ("Награда", f"{reward:,} 💎", True)
            ],
            user=user
        )
    
    async def log_shop_purchase(
        self,
        guild: discord.Guild,
        user: discord.User,
        item_name: str,
        price: int
    ):
        """Логировать покупку в магазине"""
        await self.log_event(
            guild=guild,
            title="🛒 Покупка в Магазине",
            description=f"{user.mention} купил **{item_name}**",
            color=Colors.ECONOMY,
            fields=[
                ("Товар", item_name, True),
                ("Цена", f"{price:,} 💎", True)
            ],
            user=user
        )
    
    # ==================== КОМАНДЫ ====================
    
    @app_commands.command(name="logs-set-channel", description="⚙️ [ADMIN] Установить канал для логов")
    @app_commands.describe(channel="Канал для отправки логов")
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Установить канал логов"""
        # Проверяем права на отправку сообщений
        if not channel.permissions_for(interaction.guild.me).send_messages:
            em = EmbedBuilder.error(
                title="Нет прав",
                description=f"У бота нет прав на отправку сообщений в {channel.mention}!",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Устанавливаем канал
        self._set_log_channel(interaction.guild.id, channel.id)
        
        em = EmbedBuilder.success(
            title="Канал логов установлен",
            description=f"Логи теперь будут отправляться в {channel.mention}",
            user=interaction.user,
            fields=[
                ("Статус", "✅ Включено", True),
                ("Канал", channel.mention, True)
            ]
        )
        
        await interaction.response.send_message(embed=em)
        
        # Отправляем тестовое сообщение в канал логов
        test_em = discord.Embed(
            title="✅ Система логирования активирована",
            description="Этот канал теперь используется для логирования событий сервера.",
            color=Colors.SUCCESS,
            timestamp=datetime.now()
        )
        test_em.add_field(
            name="Логируемые события",
            value="• 💰 Экономические транзакции\n"
                  "• 📊 Изменения уровней\n"
                  "• 🎮 Результаты игр\n"
                  "• ⚙️ Административные действия\n"
                  "• 🏆 Достижения\n"
                  "• 🛒 Покупки в магазине",
            inline=False
        )
        test_em.set_footer(
            text=f"Настроено: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        await channel.send(embed=test_em)
    
    @app_commands.command(name="logs-disable", description="⚙️ [ADMIN] Отключить логи")
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_disable(self, interaction: discord.Interaction):
        """Отключить логи"""
        if not self._is_enabled(interaction.guild.id):
            em = EmbedBuilder.error(
                title="Логи уже отключены",
                description="Система логов уже отключена на этом сервере.",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        self._disable_logs(interaction.guild.id)
        
        em = EmbedBuilder.success(
            title="Логи отключены",
            description="Система логов отключена. Используйте `/logs-set-channel` для включения.",
            user=interaction.user
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="logs-status", description="⚙️ [ADMIN] Проверить статус системы логов")
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_status(self, interaction: discord.Interaction):
        """Показать статус системы логов"""
        is_enabled = self._is_enabled(interaction.guild.id)
        channel_id = self._get_log_channel(interaction.guild.id)
        
        if not is_enabled or not channel_id:
            em = EmbedBuilder.info(
                title="Статус системы логов",
                description="Система логов **отключена** на этом сервере.",
                user=interaction.user,
                fields=[
                    ("Статус", "❌ Отключено", True),
                    ("Канал", "Не настроен", True),
                    ("Подсказка", "Используйте `/logs-set-channel` для настройки", False)
                ]
            )
        else:
            channel = interaction.guild.get_channel(channel_id)
            channel_text = channel.mention if channel else f"ID: {channel_id} (не найден)"
            
            em = EmbedBuilder.info(
                title="Статус системы логов",
                description="Система логов **активна** на этом сервере.",
                user=interaction.user,
                fields=[
                    ("Статус", "✅ Включено", True),
                    ("Канал", channel_text, True),
                    ("События", "Экономика, Уровни, Игры, Админ-действия", False)
                ]
            )
        
        await interaction.response.send_message(embed=em)
    
    # Обработка ошибок для admin команд
    @logs_set_channel.error
    @logs_disable.error
    @logs_status.error
    async def admin_command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для использования этой команды!",
                ephemeral=True
            )
    
    @app_commands.command(name="logs-view", description="📋 [ADMIN] Просмотр логов")
    @app_commands.describe(
        event_type="Тип события (все/economy/games/levels)",
        limit="Количество записей (макс 50)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_view(
        self, 
        interaction: discord.Interaction,
        event_type: str = "all",
        limit: int = 10
    ):
        """Просмотр последних логов"""
        if limit < 1 or limit > 50:
            await interaction.response.send_message("❌ Limit должен быть от 1 до 50!", ephemeral=True)
            return
        
        logs = self._load_logs_data()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in logs or not logs[guild_id]:
            em = EmbedBuilder.info(
                title="📋 Логи Пусты",
                description="Нет сохранённых логов для этого сервера",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        guild_logs = logs[guild_id]
        
        # Фильтрация
        if event_type != "all":
            guild_logs = [log for log in guild_logs if log.get("type") == event_type]
        
        # Последние N записей
        guild_logs = guild_logs[-limit:]
        guild_logs.reverse()
        
        if not guild_logs:
            em = EmbedBuilder.info(
                title="📋 Логи Не Найдены",
                description=f"Нет логов типа **{event_type}**",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Форматирование
        description = ""
        for i, log in enumerate(guild_logs[:10], 1):
            timestamp = datetime.fromisoformat(log["timestamp"]).strftime("%d.%m %H:%M")
            log_type = log.get("type", "unknown")
            data = log.get("data", {})
            
            if log_type == "economy":
                description += f"`{timestamp}` 💰 {data.get('user_name')}: {data.get('transaction_type')} ({data.get('amount'):,}💎)\n"
            else:
                description += f"`{timestamp}` {log_type}: {str(data)[:50]}\n"
        
        em = EmbedBuilder.info(
            title="📋 Логи Сервера",
            description=description or "Нет данных",
            user=interaction.user
        )
        em.set_footer(text=f"Показано: {min(len(guild_logs), 10)} из {len(guild_logs)}")
        
        await interaction.response.send_message(embed=em, ephemeral=True)
    
    @app_commands.command(name="logs-export", description="💾 [ADMIN] Экспортировать логи")
    @app_commands.describe(format="Формат экспорта")
    @app_commands.choices(format=[
        app_commands.Choice(name="TXT", value="txt"),
        app_commands.Choice(name="JSON", value="json"),
        app_commands.Choice(name="CSV", value="csv")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_export(self, interaction: discord.Interaction, format: str):
        """Экспортировать логи в файл"""
        logs = self._load_logs_data()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in logs or not logs[guild_id]:
            await interaction.response.send_message("❌ Нет логов для экспорта!", ephemeral=True)
            return
        
        guild_logs = logs[guild_id]
        filename = f"logs_{interaction.guild.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        import io
        
        if format == "txt":
            content = f"Логи сервера {interaction.guild.name}\nЭкспортировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            for log in guild_logs:
                timestamp = datetime.fromisoformat(log["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                content += f"[{timestamp}] {log.get('type')}: {log.get('data')}\n"
            
            file_data = io.BytesIO(content.encode('utf-8'))
        
        elif format == "json":
            import json
            content = json.dumps(guild_logs, ensure_ascii=False, indent=2)
            file_data = io.BytesIO(content.encode('utf-8'))
        
        elif format == "csv":
            content = "Timestamp,Type,User,Details\n"
            for log in guild_logs:
                timestamp = datetime.fromisoformat(log["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                log_type = log.get('type', '')
                data = log.get('data', {})
                user_name = data.get('user_name', '')
                details = str(data).replace(",", ";")
                content += f"{timestamp},{log_type},{user_name},{details}\n"
            
            file_data = io.BytesIO(content.encode('utf-8'))
        
        file_data.seek(0)
        file = discord.File(file_data, filename=filename)
        
        em = EmbedBuilder.success(
            title="💾 Логи Экспортированы",
            description=f"Экспортировано **{len(guild_logs)}** записей",
            user=interaction.user,
            fields=[
                ("Формат", format.upper(), True),
                ("Записей", str(len(guild_logs)), True)
            ]
        )
        
        await interaction.response.send_message(embed=em, file=file, ephemeral=True)
    
    @app_commands.command(name="logs-search", description="🔍 [ADMIN] Поиск в логах")
    @app_commands.describe(query="Поисковый запрос")
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_search(self, interaction: discord.Interaction, query: str):
        """Поиск в логах"""
        logs = self._load_logs_data()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in logs or not logs[guild_id]:
            await interaction.response.send_message("❌ Нет логов для поиска!", ephemeral=True)
            return
        
        guild_logs = logs[guild_id]
        query_lower = query.lower()
        
        # Поиск
        results = []
        for log in guild_logs:
            log_str = json.dumps(log, ensure_ascii=False).lower()
            if query_lower in log_str:
                results.append(log)
        
        if not results:
            em = EmbedBuilder.info(
                title="🔍 Поиск в Логах",
                description=f"По запросу **{query}** ничего не найдено",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Показываем первые 10
        description = f"Найдено: **{len(results)}** записей\n\n"
        for i, log in enumerate(results[-10:], 1):
            timestamp = datetime.fromisoformat(log["timestamp"]).strftime("%d.%m %H:%M")
            log_type = log.get("type", "unknown")
            description += f"`{timestamp}` {log_type}\n"
        
        em = EmbedBuilder.info(
            title=f"🔍 Результаты Поиска: {query}",
            description=description,
            user=interaction.user
        )
        em.set_footer(text=f"Показано последних 10 из {len(results)}")
        
        await interaction.response.send_message(embed=em, ephemeral=True)
    
    @logs_view.error
    @logs_export.error
    @logs_search.error
    async def logs_extended_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для использования этой команды!",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Logs(bot))
