# help.py
"""Система помощи с красивым интерактивным меню"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import os
from utils.embed_builder import EmbedBuilder, Colors


class HelpCog(commands.Cog):
    """Ког для команды помощи"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Определение категорий команд
        self.categories = {
            "💰 Экономика": {
                "description": "Команды для зарабатывания и управления крионами",
                "commands": [
                    ("balance", "Посмотреть баланс"),
                    ("daily", "Получить ежедневную награду"),
                    ("work", "Поработать и заработать крионы"),
                    ("weekly", "Получить еженедельную награду"),
                    ("monthly", "Получить ежемесячную награду"),
                    ("transfer", "Передать крионы другому пользователю"),
                    ("leaderboard", "Топ самых богатых пользователей"),
                    ("history", "История транзакций"),
                ],
                "admin": False
            },
            "🛒 Магазин": {
                "description": "Покупка товаров и управление инвентарём",
                "commands": [
                    ("shop", "Посмотреть магазин"),
                    ("buy", "Купить товар из магазина"),
                    ("inventory", "Посмотреть свой инвентарь"),
                ],
                "admin": False
            },
            "🎮 Игры": {
                "description": "Азартные игры и развлечения",
                "commands": [
                    ("slots", "Сыграть в игровой автомат"),
                    ("roulette", "Сыграть в рулетку"),
                    ("coinflip", "Подбросить монетку"),
                    ("achievements", "Просмотр достижений"),
                ],
                "admin": False
            },
            "📊 Уровни": {
                "description": "Система уровней и опыта",
                "commands": [
                    ("level", "Посмотреть свой уровень и прогресс"),
                    ("rank", "Топ пользователей по уровню"),
                    ("dailyxp", "Получить ежедневный бонус опыта"),
                    ("levelnotify", "Включить/выключить уведомления о повышении уровня"),
                ],
                "admin": False
            },
            "⚙️ Администрирование": {
                "description": "Команды для администраторов сервера",
                "commands": [
                    ("eco-add", "[ADMIN] Добавить крионы пользователю"),
                    ("eco-remove", "[ADMIN] Убрать крионы у пользователя"),
                    ("eco-set", "[ADMIN] Установить баланс пользователю"),
                    ("eco-reset", "[ADMIN] Сбросить экономику"),
                    ("shop-add", "[ADMIN] Добавить товар в магазин"),
                    ("shop-remove", "[ADMIN] Удалить товар из магазина"),
                    ("shop-edit", "[ADMIN] Изменить товар в магазине"),
                    ("setxp", "[ADMIN] Установить XP пользователю"),
                    ("setlevel", "[ADMIN] Установить уровень пользователю"),
                    ("logs-set-channel", "[ADMIN] Установить канал для логов"),
                    ("logs-disable", "[ADMIN] Отключить логи"),
                    ("logs-status", "[ADMIN] Статус системы логов"),
                ],
                "admin": True
            },
            "🔧 Система": {
                "description": "Системные команды и утилиты",
                "commands": [
                    ("help", "Показать это меню помощи"),
                    ("sync", "[OWNER] Синхронизировать команды глобально"),
                    ("syncguild", "[OWNER] Синхронизировать команды для гильдии"),
                ],
                "admin": False
            }
        }
    
    def _is_admin(self, interaction: discord.Interaction) -> bool:
        """Проверка является ли пользователь администратором"""
        return interaction.user.guild_permissions.administrator or interaction.user.id == self.bot.owner_id
    
    @app_commands.command(name="help", description="📚 Справка по командам бота")
    @app_commands.describe(category="Выберите категорию для подробной информации")
    async def help_command(
        self, 
        interaction: discord.Interaction,
        category: Optional[str] = None
    ):
        """Показать справку по командам"""
        is_admin = self._is_admin(interaction)
        
        if category:
            # Показываем конкретную категорию
            await self._show_category(interaction, category, is_admin)
        else:
            # Показываем общее меню
            await self._show_main_menu(interaction, is_admin)
    
    async def _show_main_menu(self, interaction: discord.Interaction, is_admin: bool):
        """Показать главное меню помощи"""
        em = discord.Embed(
            title="📚 Справка по командам бота",
            description="Выберите категорию для просмотра команд\n\n"
                       "Используйте `/help [категория]` для подробной информации",
            color=Colors.PRIMARY,
            timestamp=discord.utils.utcnow()
        )
        
        em.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        # Добавляем категории
        for category_name, category_data in self.categories.items():
            # Скрываем админские категории от обычных пользователей
            if category_data["admin"] and not is_admin:
                continue
            
            command_count = len(category_data["commands"])
            em.add_field(
                name=f"{category_name}",
                value=f"{category_data['description']}\n`{command_count} команд`",
                inline=False
            )
        
        em.add_field(
            name="💡 Подсказка",
            value="Все команды используются через `/` (slash команды)",
            inline=False
        )
        
        em.set_footer(
            text=f"Запрос от {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        # Создаём dropdown для выбора категории
        view = HelpView(self, is_admin)
        await interaction.response.send_message(embed=em, view=view)
    
    async def _show_category(self, interaction: discord.Interaction, category_key: str, is_admin: bool):
        """Показать команды конкретной категории"""
        # Находим категорию
        category_data = None
        category_name = None
        
        for cat_name, cat_data in self.categories.items():
            if cat_name.lower().replace(" ", "") == category_key.lower().replace(" ", ""):
                category_data = cat_data
                category_name = cat_name
                break
        
        if not category_data:
            await interaction.response.send_message(
                "❌ Категория не найдена! Используйте `/help` для списка категорий.",
                ephemeral=True
            )
            return
        
        # Проверка прав для админских категорий
        if category_data["admin"] and not is_admin:
            await interaction.response.send_message(
                "❌ У вас нет доступа к этой категории команд!",
                ephemeral=True
            )
            return
        
        em = discord.Embed(
            title=f"{category_name}",
            description=category_data["description"],
            color=Colors.ACCENT,
            timestamp=discord.utils.utcnow()
        )
        
        em.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        # Добавляем команды
        for cmd_name, cmd_desc in category_data["commands"]:
            em.add_field(
                name=f"/{cmd_name}",
                value=cmd_desc,
                inline=False
            )
        
        em.set_footer(
            text=f"Запрос от {interaction.user.display_name} • Используйте /help для возврата в меню",
            icon_url=interaction.user.display_avatar.url
        )
        
        # Если это был вызов через interaction response
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=em)
        else:
            await interaction.followup.send(embed=em)


class HelpView(discord.ui.View):
    """View с dropdown для выбора категории"""
    
    def __init__(self, help_cog, is_admin: bool):
        super().__init__(timeout=180)
        self.help_cog = help_cog
        self.add_item(CategorySelect(help_cog, is_admin))


class CategorySelect(discord.ui.Select):
    """Dropdown для выбора категории"""
    
    def __init__(self, help_cog, is_admin: bool):
        self.help_cog = help_cog
        
        # Создаём опции для dropdown
        options = []
        for category_name, category_data in help_cog.categories.items():
            # Скрываем админские категории от обычных пользователей
            if category_data["admin"] and not is_admin:
                continue
            
            # Извлекаем эмодзи из названия категории
            emoji = category_name.split()[0] if category_name else "📁"
            label = category_name.replace(emoji, "").strip()
            
            options.append(
                discord.SelectOption(
                    label=label,
                    description=category_data["description"][:100],
                    emoji=emoji,
                    value=category_name
                )
            )
        
        super().__init__(
            placeholder="Выберите категорию...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Обработка выбора категории"""
        selected_category = self.values[0]
        is_admin =interaction.user.guild_permissions.administrator or interaction.user.id == self.help_cog.bot.owner_id
        
        # Получаем данные категории
        category_data = self.help_cog.categories.get(selected_category)
        
        if not category_data:
            await interaction.response.send_message(
                "❌ Ошибка при получении категории!",
                ephemeral=True
            )
            return
        
        em = discord.Embed(
            title=f"{selected_category}",
            description=category_data["description"],
            color=Colors.ACCENT,
            timestamp=discord.utils.utcnow()
        )
        
        em.set_thumbnail(url=self.help_cog.bot.user.display_avatar.url)
        
        # Добавляем команды
        for cmd_name, cmd_desc in category_data["commands"]:
            em.add_field(
                name=f"/{cmd_name}",
                value=cmd_desc,
                inline=False
            )
        
        em.set_footer(
            text=f"Запрос от {interaction.user.display_name} • Выберите другую категорию из списка",
            icon_url=interaction.user.display_avatar.url
        )
        
        # Обновляем сообщение
        await interaction.response.edit_message(embed=em)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
