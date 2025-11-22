# business.py - Система бизнеса
"""Создание и управление бизнесами: пассивный доход, найм работников"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Literal
from utils.embed_builder import EmbedBuilder, Colors


class Business(commands.Cog):
    """Система управления бизнесами"""
    
    def __init__(self, bot):
        self.bot = bot
        self.business_file = 'business.json'
        self.currency_emoji = "💎"
        
        # Типы бизнесов с их характеристиками
        self.business_types = {
            "shop": {
                "name": "🏪 Магазин",
                "cost": 10000,
                "income_per_hour": 100,
                "required_level": 1,
                "description": "Небольшой магазин с базовым доходом"
            },
            "restaurant": {
                "name": "🍽️ Ресторан",
                "cost": 25000,
                "income_per_hour": 150,
                "required_level": 10,
                "description": "Уютный ресторан с хорошим доходом"
            },
            "casino": {
                "name": "🎰 Казино",
                "cost": 50000,
                "income_per_hour": 200,
                "required_level": 20,
                "description": "Прибыльное казино для опытных"
            },
            "corporation": {
                "name": "🏢 Корпорация",
                "cost": 100000,
                "income_per_hour": 300,
                "required_level": 30,
                "description": "Огромная корпорация с максимальным доходом"
            }
        }
        
        self._ensure_file()
        self.collect_income.start()
    
    def _ensure_file(self):
        """Создание файла если его нет"""
        if not os.path.exists(self.business_file):
            with open(self.business_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
    
    def _load_businesses(self) -> dict:
        """Загрузка данных бизнесов"""
        with open(self.business_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_businesses(self, data: dict):
        """Сохранение данных бизнесов"""
        with open(self.business_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def _get_user_level(self, user_id: str) -> int:
        """Получить уровень пользователя"""
        levels_cog = self.bot.get_cog('Levels')
        if levels_cog:
            user_data = levels_cog._get_user_data(user_id)
            return user_data.get('level', 1)
        return 1
    
    def _get_economy_balance(self, user_id: str) -> int:
        """Получить баланс из экономики"""
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            return economy_cog._get_user_data(user_id).get('balance', 0)
        return 0
    
    def _update_economy_balance(self, user_id: str, amount: int):
        """Обновить баланс в экономике"""
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            economy_cog._update_balance(user_id, amount)
            economy_cog._add_transaction(user_id, "business", amount, "Доход от бизнеса")
    
    def _calculate_income(self, business_data: dict) -> int:
        """Расчёт дохода бизнеса"""
        business_type = business_data["type"]
        base_income = self.business_types[business_type]["income_per_hour"]
        
        # Бонус от работников (10% за каждого)
        employees = business_data.get("employees", [])
        employee_bonus = len(employees) * 0.10
        
        total_income = int(base_income * (1 + employee_bonus))
        return total_income
    
    @tasks.loop(hours=6)
    async def collect_income(self):
        """Автоматический сбор дохода каждые 6 часов"""
        businesses = self._load_businesses()
        
        for user_id, user_businesses in businesses.items():
            total_income = 0
            
            for business_id, business_data in user_businesses.items():
                # Проверяем время последнего сбора
                last_collect = business_data.get("last_collect")
                if last_collect:
                    last_time = datetime.fromisoformat(last_collect)
                    hours_passed = (datetime.now() - last_time).total_seconds() / 3600
                    
                    # Максимум 24 часа накопления
                    hours_passed = min(hours_passed, 24)
                    
                    income = self._calculate_income(business_data)
                    earned = int(income * hours_passed)
                    total_income += earned
                
                # Обновляем время
                business_data["last_collect"] = datetime.now().isoformat()
            
            if total_income > 0:
                self._update_economy_balance(user_id, total_income)
        
        if businesses:
            self._save_businesses(businesses)
    
    @collect_income.before_loop
    async def before_collect_income(self):
        await self.bot.wait_until_ready()
    
    @app_commands.command(name="business-create", description="🏢 Создать бизнес")
    @app_commands.describe(
        business_type="Тип бизнеса",
        name="Название бизнеса"
    )
    @app_commands.choices(business_type=[
        app_commands.Choice(name="🏪 Магазин (10,000💎, ур.1)", value="shop"),
        app_commands.Choice(name="🍽️ Ресторан (25,000💎, ур.10)", value="restaurant"),
        app_commands.Choice(name="🎰 Казино (50,000💎, ур.20)", value="casino"),
        app_commands.Choice(name="🏢 Корпорация (100,000💎, ур.30)", value="corporation")
    ])
    async def business_create(
        self, 
        interaction: discord.Interaction, 
        business_type: str,
        name: str
    ):
        """Создать новый бизнес"""
        user_id = str(interaction.user.id)
        
        # Проверка типа
        if business_type not in self.business_types:
            await interaction.response.send_message("❌ Неверный тип бизнеса!", ephemeral=True)
            return
        
        biz_info = self.business_types[business_type]
        
        # Проверка уровня
        user_level = self._get_user_level(user_id)
        if user_level < biz_info["required_level"]:
            em = EmbedBuilder.error(
                title="Недостаточный уровень!",
                description=f"Для {biz_info['name']} нужен {biz_info['required_level']} уровень\nУ вас: {user_level} уровень",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Проверка баланса
        balance = self._get_economy_balance(user_id)
        if balance < biz_info["cost"]:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"Нужно: **{biz_info['cost']:,}**{self.currency_emoji}\nУ вас: **{balance:,}**{self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Создаём бизнес
        businesses = self._load_businesses()
        if user_id not in businesses:
            businesses[user_id] = {}
        
        # Лимит 3 бизнеса
        if len(businesses[user_id]) >= 3:
            await interaction.response.send_message("❌ У вас уже максимум бизнесов (3)!", ephemeral=True)
            return
        
        # Уникальный ID
        business_id = f"biz_{len(businesses[user_id]) + 1}"
        
        businesses[user_id][business_id] = {
            "name": name,
            "type": business_type,
            "created": datetime.now().isoformat(),
            "last_collect": datetime.now().isoformat(),
            "employees": []
        }
        
        self._save_businesses(businesses)
        self._update_economy_balance(user_id, -biz_info["cost"])
        
        em = EmbedBuilder.success(
            title="Бизнес Создан!",
            description=f"Поздравляем с открытием **{name}**!",
            user=interaction.user,
            fields=[
                ("Тип", biz_info["name"], True),
                ("Стоимость", f"{biz_info['cost']:,}{self.currency_emoji}", True),
                ("Доход", f"{biz_info['income_per_hour']:,}{self.currency_emoji}/час", True),
                ("ID", f"`{business_id}`", True)
            ]
        )
        em.set_footer(text="Доход собирается автоматически каждые 6 часов или командой /business-collect")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="business-manage", description="⚙️ Управление бизнесами")
    async def business_manage(self, interaction: discord.Interaction):
        """Показать все бизнесы пользователя"""
        user_id = str(interaction.user.id)
        businesses = self._load_businesses()
        
        if user_id not in businesses or not businesses[user_id]:
            em = EmbedBuilder.info(
                title="У вас нет бизнесов",
                description="Создайте бизнес командой `/business-create`!",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        fields = []
        total_income_per_hour = 0
        
        for biz_id, biz_data in businesses[user_id].items():
            biz_type = biz_data["type"]
            biz_info = self.business_types[biz_type]
            income = self._calculate_income(biz_data)
            total_income_per_hour += income
            
            employee_count = len(biz_data.get("employees", []))
            
            fields.append((
                f"{biz_info['name']} - {biz_data['name']}",
                f"ID: `{biz_id}`\n"
                f"Доход: **{income:,}**{self.currency_emoji}/час\n"
                f"Работников: {employee_count}/5",
                False
            ))
        
        fields.append((
            "💰 Общий доход",
            f"**{total_income_per_hour:,}**{self.currency_emoji}/час",
            False
        ))
        
        em = EmbedBuilder.economy(
            title="Ваши Бизнесы",
            description=f"Управление бизнесами {interaction.user.display_name}",
            user=interaction.user,
            fields=fields,
            footer_text=f"Всего бизнесов: {len(businesses[user_id])}/3"
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="business-collect", description="💰 Собрать доход с бизнесов")
    async def business_collect(self, interaction: discord.Interaction):
        """Собрать накопленный доход"""
        user_id = str(interaction.user.id)
        businesses = self._load_businesses()
        
        if user_id not in businesses or not businesses[user_id]:
            await interaction.response.send_message("❌ У вас нет бизнесов!", ephemeral=True)
            return
        
        total_income = 0
        details = []
        
        for biz_id, biz_data in businesses[user_id].items():
            last_collect = biz_data.get("last_collect")
            if not last_collect:
                biz_data["last_collect"] = datetime.now().isoformat()
                continue
            
            last_time = datetime.fromisoformat(last_collect)
            hours_passed = (datetime.now() - last_time).total_seconds() / 3600
            
            if hours_passed < 0.1:  # Менее 6 минут
                continue
            
            # Максимум 24 часа
            hours_passed = min(hours_passed, 24)
            
            income = self._calculate_income(biz_data)
            earned = int(income * hours_passed)
            total_income += earned
            
            biz_type = biz_data["type"]
            biz_info = self.business_types[biz_type]
            details.append((
                f"{biz_info['name']} - {biz_data['name']}",
                f"+{earned:,}{self.currency_emoji} ({hours_passed:.1f}ч)",
                True
            ))
            
            # Обновляем время
            biz_data["last_collect"] = datetime.now().isoformat()
        
        if total_income == 0:
            await interaction.response.send_message("❌ Пока нет дохода для сбора!", ephemeral=True)
            return
        
        self._save_businesses(businesses)
        self._update_economy_balance(user_id, total_income)
        
        em = EmbedBuilder.success(
            title="Доход Собран!",
            description=f"Вы получили **{total_income:,}**{self.currency_emoji} от ваших бизнесов!",
            user=interaction.user,
            fields=details
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="business-hire", description="👔 Нанять работника")
    @app_commands.describe(
        business_id="ID бизнеса",
        user="Пользователь для найма"
    )
    async def business_hire(
        self,
        interaction: discord.Interaction,
        business_id: str,
        user: discord.Member
    ):
        """Нанять работника в бизнес"""
        owner_id = str(interaction.user.id)
        employee_id = str(user.id)
        
        if user.bot:
            await interaction.response.send_message("❌ Нельзя нанять бота!", ephemeral=True)
            return
        
        if owner_id == employee_id:
            await interaction.response.send_message("❌ Нельзя нанять самого себя!", ephemeral=True)
            return
        
        businesses = self._load_businesses()
        
        if owner_id not in businesses or business_id not in businesses[owner_id]:
            await interaction.response.send_message("❌ Бизнес не найден!", ephemeral=True)
            return
        
        biz_data = businesses[owner_id][business_id]
        employees = biz_data.get("employees", [])
        
        if len(employees) >= 5:
            await interaction.response.send_message("❌ Максимум 5 работников!", ephemeral=True)
            return
        
        if employee_id in employees:
            await interaction.response.send_message(f"❌ {user.display_name} уже работает здесь!", ephemeral=True)
            return
        
        # Нанимаем
        employees.append(employee_id)
        biz_data["employees"] = employees
        self._save_businesses(businesses)
        
        biz_info = self.business_types[biz_data["type"]]
        new_income = self._calculate_income(biz_data)
        
        em = EmbedBuilder.success(
            title="Работник Нанят!",
            description=f"{user.mention} теперь работает в **{biz_data['name']}**!",
            user=interaction.user,
            fields=[
                ("Бизнес", biz_info["name"], True),
                ("Работников", f"{len(employees)}/5", True),
                ("Новый доход", f"{new_income:,}{self.currency_emoji}/час", True)
            ]
        )
        em.set_footer(text="Каждый работник даёт +10% к доходу")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="business-fire", description="🚪 Уволить работника")
    @app_commands.describe(
        business_id="ID бизнеса",
        user="Пользователь для увольнения"
    )
    async def business_fire(
        self,
        interaction: discord.Interaction,
        business_id: str,
        user: discord.Member
    ):
        """Уволить работника"""
        owner_id = str(interaction.user.id)
        employee_id = str(user.id)
        
        businesses = self._load_businesses()
        
        if owner_id not in businesses or business_id not in businesses[owner_id]:
            await interaction.response.send_message("❌ Бизнес не найден!", ephemeral=True)
            return
        
        biz_data = businesses[owner_id][business_id]
        employees = biz_data.get("employees", [])
        
        if employee_id not in employees:
            await interaction.response.send_message(f"❌ {user.display_name} не работает здесь!", ephemeral=True)
            return
        
        # Увольняем
        employees.remove(employee_id)
        biz_data["employees"] = employees
        self._save_businesses(businesses)
        
        em = EmbedBuilder.info(
            title="Работник Уволен",
            description=f"{user.mention} больше не работает в **{biz_data['name']}**",
            user=interaction.user,
            fields=[
                ("Осталось работников", f"{len(employees)}/5", True)
            ]
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="business-stats", description="📊 Статистика бизнеса")
    @app_commands.describe(business_id="ID бизнеса")
    async def business_stats(self, interaction: discord.Interaction, business_id: str):
        """Показать детальную статистику бизнеса"""
        user_id = str(interaction.user.id)
        businesses = self._load_businesses()
        
        if user_id not in businesses or business_id not in businesses[user_id]:
            await interaction.response.send_message("❌ Бизнес не найден!", ephemeral=True)
            return
        
        biz_data = businesses[user_id][business_id]
        biz_info = self.business_types[biz_data["type"]]
        
        created = datetime.fromisoformat(biz_data["created"])
        days_active = (datetime.now() - created).days
        
        income_per_hour = self._calculate_income(biz_data)
        income_per_day = income_per_hour * 24
        
        employees = biz_data.get("employees", [])
        employee_names = []
        for emp_id in employees[:5]:
            try:
                emp_user = await self.bot.fetch_user(int(emp_id))
                employee_names.append(emp_user.display_name)
            except:
                pass
        
        fields = [
            ("Тип", biz_info["name"], True),
            ("Доход/час", f"{income_per_hour:,}{self.currency_emoji}", True),
            ("Доход/день", f"{income_per_day:,}{self.currency_emoji}", True),
            ("Работников", f"{len(employees)}/5", True),
            ("Дней активен", str(days_active), True)
        ]
        
        if employee_names:
            fields.append(("Работники", ", ".join(employee_names), False))
        
        em = EmbedBuilder.info(
            title=f"📊 {biz_data['name']}",
            description=biz_info["description"],
            user=interaction.user,
            fields=fields,
            footer_text=f"ID: {business_id}"
        )
        
        await interaction.response.send_message(embed=em)


async def setup(bot):
    await bot.add_cog(Business(bot))
