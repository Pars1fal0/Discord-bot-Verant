# bank.py
"""Банковская система: депозиты, кредиты"""
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta
from typing import Optional
from utils.embed_builder import EmbedBuilder, Colors


class Bank(commands.Cog):
    """Банковская система"""
    
    def __init__(self, bot):
        self.bot = bot
        self.bank_file = 'bank.json'
        self.currency_emoji = "💎"
        self.deposit_rate = 0.03  # 3% годовых (в день: 3%/365)
        self.loan_rate = 0.10  # 10% процент на кредит
        self._ensure_file()
    
    def _ensure_file(self):
        """Создание файла банка если его нет"""
        if not os.path.exists(self.bank_file):
            with open(self.bank_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
    
    def _load_bank(self) -> dict:
        """Загрузка банковских данных"""
        with open(self.bank_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_bank(self, data: dict):
        """Сохранение банковских данных"""
        with open(self.bank_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def _get_user_data(self, user_id: str) -> dict:
        """Получение банковских данных пользователя"""
        bank = self._load_bank()
        if user_id not in bank:
            bank[user_id] = {
                "deposit": 0,
                "deposit_since": None,
                "loan": 0,
                "loan_since": None,
                "loan_deadline": None
            }
            self._save_bank(bank)
        return bank[user_id]
    
    def _get_economy_balance(self, user_id: str) -> int:
        """Получить баланс из экономики"""
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            user_data = economy_cog._get_user_data(user_id)
            return user_data.get('balance', 0)
        return 0
    
    def _update_economy_balance(self, user_id: str, amount: int):
        """Обновить баланс в экономике"""
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            economy_cog._update_balance(user_id, amount)
            economy_cog._add_transaction(user_id, "bank", amount, "Банковская транзакция")
    
    def _calculate_deposit_interest(self, amount: int, days: float) -> int:
        """Рассчитать проценты по депозиту"""
        daily_rate = self.deposit_rate / 365
        interest = int(amount * daily_rate * days)
        return interest
    
    @app_commands.command(name="bank", description="🏦 Просмотр банковского счёта")
    async def bank_account(self, interaction: discord.Interaction):
        """Показать информацию о банковском счёте"""
        user_id = str(interaction.user.id)
        bank_data = self._get_user_data(user_id)
        wallet_balance = self._get_economy_balance(user_id)
        
        # Рассчитываем проценты по депозиту
        deposit_interest = 0
        if bank_data["deposit"] > 0 and bank_data["deposit_since"]:
            deposit_since = datetime.fromisoformat(bank_data["deposit_since"])
            days = (datetime.now() - deposit_since).total_seconds() / 86400
            deposit_interest = self._calculate_deposit_interest(bank_data["deposit"], days)
        
        fields = [
            ("💰 Кошелёк", f"{wallet_balance:,} {self.currency_emoji}", True),
            ("📈 Депозит", f"{bank_data['deposit']:,} {self.currency_emoji}", True),
            ("💵 Начисленные проценты", f"+{deposit_interest:,} {self.currency_emoji}", True)
        ]
        
        if bank_data["loan"] > 0:
            loan_deadline = datetime.fromisoformat(bank_data["loan_deadline"])
            days_left = (loan_deadline - datetime.now()).days
            fields.append(("💳 Кредит", f"{bank_data['loan']:,} {self.currency_emoji}", True))
            fields.append(("⏰ Осталось дней", f"{days_left} дней", True))
        
        total = wallet_balance + bank_data["deposit"] + deposit_interest - bank_data["loan"]
        fields.append(("💎 Общий капитал", f"{total:,} {self.currency_emoji}", False))
        
        em = EmbedBuilder.economy(
            title="Банковский Счёт",
            description=f"Информация о счёте **{interaction.user.display_name}**",
            user=interaction.user,
            fields=fields,
            footer_text="Депозиты приносят 3% годовых"
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="deposit", description="📈 Положить деньги на депозит")
    @app_commands.describe(amount="Сумма для депозита")
    async def deposit(self, interaction: discord.Interaction, amount: int):
        """Положить деньги на депозит"""
        if amount <= 0:
            await interaction.response.send_message("❌ Сумма должна быть больше 0!", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        balance = self._get_economy_balance(user_id)
        
        if balance < amount:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"У вас всего **{balance:,}** {self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        bank_data = self._load_bank()
        if user_id not in bank_data:
            self._get_user_data(user_id)
            bank_data = self._load_bank()
        
        # Снимаем с кошелька
        self._update_economy_balance(user_id, -amount)
        
        # Добавляем на депозит
        if bank_data[user_id]["deposit"] == 0:
            bank_data[user_id]["deposit_since"] = datetime.now().isoformat()
        
        bank_data[user_id]["deposit"] += amount
        self._save_bank(bank_data)
        
        em = EmbedBuilder.success(
            title="Депозит Оформлен!",
            description=f"Вы положили **{amount:,}** {self.currency_emoji} на депозит",
            user=interaction.user,
            fields=[
                ("💰 Ставка", "3% годовых", True),
                ("📈 Общий депозит", f"{bank_data[user_id]['deposit']:,} {self.currency_emoji}", True)
            ]
        )
        em.set_footer(text="Проценты начисляются ежедневно. Используйте /withdraw для снятия")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="withdraw", description="💰 Снять деньги с депозита")
    @app_commands.describe(amount="Сумма для снятия (или 'all' для снятия всего)")
    async def withdraw(self, interaction: discord.Interaction, amount: str):
        """Снять деньги с депозита"""
        user_id = str(interaction.user.id)
        bank_data = self._get_user_data(user_id)
        
        if bank_data["deposit"] == 0:
            await interaction.response.send_message("❌ У вас нет денег на депозите!", ephemeral=True)
            return
        
        # Рассчитываем проценты
        deposit_since = datetime.fromisoformat(bank_data["deposit_since"])
        days = (datetime.now() - deposit_since).total_seconds() / 86400
        interest = self._calculate_deposit_interest(bank_data["deposit"], days)
        
        # Определяем сумму для снятия
        if amount.lower() == "all":
            withdraw_amount = bank_data["deposit"] + interest
        else:
            try:
                withdraw_amount = int(amount)
            except ValueError:
                await interaction.response.send_message("❌ Введите корректную сумму или 'all'!", ephemeral=True)
                return
        
        total_available = bank_data["deposit"] + interest
        if withdraw_amount > total_available:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"Доступно: **{total_available:,}** {self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Выполняем снятие
        bank = self._load_bank()
        bank[user_id]["deposit"] = max(0, total_available - withdraw_amount)
        if bank[user_id]["deposit"] == 0:
            bank[user_id]["deposit_since"] = None
        else:
            bank[user_id]["deposit_since"] = datetime.now().isoformat()
        self._save_bank(bank)
        
        # Добавляем в кошелёк
        self._update_economy_balance(user_id, withdraw_amount)
        
        em = EmbedBuilder.success(
            title="Снятие Выполнено!",
            description=f"Вы сняли **{withdraw_amount:,}** {self.currency_emoji}",
            user=interaction.user,
            fields=[
                ("💰 Основная сумма", f"{bank_data['deposit']:,} {self.currency_emoji}", True),
                ("📈 Проценты", f"+{interest:,} {self.currency_emoji}", True),
                ("📊 Осталось на депозите", f"{bank[user_id]['deposit']:,} {self.currency_emoji}", False)
            ]
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="loan", description="💳 Взять кредит")
    @app_commands.describe(amount="Сумма кредита")
    async def loan(self, interaction: discord.Interaction, amount: int):
        """Взять кредит в банке"""
        if amount <= 0:
            await interaction.response.send_message("❌ Сумма должна быть больше 0!", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        bank_data = self._get_user_data(user_id)
        balance = self._get_economy_balance(user_id)
        
        # Проверка наличия активного кредита
        if bank_data["loan"] > 0:
            await interaction.response.send_message("❌ У вас уже есть активный кредит! Погасите его сначала.", ephemeral=True)
            return
        
        # Лимит кредита - 50% от текущего баланса, но минимум 1000
        max_loan = max(int(balance * 0.5), 1000)
        
        if amount > max_loan:
            em = EmbedBuilder.error(
                title="Превышен лимит кредита!",
                description=f"Максимальный кредит: **{max_loan:,}** {self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Выдаём кредит
        loan_with_interest = int(amount * (1 + self.loan_rate))
        deadline = datetime.now() + timedelta(days=7)
        
        bank = self._load_bank()
        bank[user_id]["loan"] = loan_with_interest
        bank[user_id]["loan_since"] = datetime.now().isoformat()
        bank[user_id]["loan_deadline"] = deadline.isoformat()
        self._save_bank(bank)
        
        # Добавляем в кошелёк
        self._update_economy_balance(user_id, amount)
        
        em = EmbedBuilder.info(
            title="Кредит Одобрен!",
            description=f"Вы получили **{amount:,}** {self.currency_emoji}",
            user=interaction.user,
            fields=[
                ("💳 Получено", f"{amount:,} {self.currency_emoji}", True),
                ("💰 К возврату", f"{loan_with_interest:,} {self.currency_emoji}", True),
                ("📊 Процент", f"{int(self.loan_rate * 100)}%", True),
                ("⏰ Срок возврата", f"{deadline.strftime('%Y-%m-%d')}", True)
            ]
        )
        em.set_footer(text="Погасите кредит командой /loan-repay до указанного срока!")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="loan-repay", description="💵 Погасить кредит")
    @app_commands.describe(amount="Сумма для погашения (или 'all' для полного погашения)")
    async def loan_repay(self, interaction: discord.Interaction, amount: str):
        """Погасить кредит"""
        user_id = str(interaction.user.id)
        bank_data = self._get_user_data(user_id)
        
        if bank_data["loan"] == 0:
            await interaction.response.send_message("❌ У вас нет активного кредита!", ephemeral=True)
            return
        
        balance = self._get_economy_balance(user_id)
        
        # Определяем сумму
        if amount.lower() == "all":
            repay_amount = bank_data["loan"]
        else:
            try:
                repay_amount = int(amount)
            except ValueError:
                await interaction.response.send_message("❌ Введите корректную сумму или 'all'!", ephemeral=True)
                return
        
        if repay_amount > bank_data["loan"]:
            repay_amount = bank_data["loan"]
        
        if balance < repay_amount:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"У вас: **{balance:,}** {self.currency_emoji}\nНужно: **{repay_amount:,}** {self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Погашаем кредит
        bank = self._load_bank()
        bank[user_id]["loan"] -= repay_amount
        
        if bank[user_id]["loan"] == 0:
            bank[user_id]["loan_since"] = None
            bank[user_id]["loan_deadline"] = None
        
        self._save_bank(bank)
        
        # Снимаем с кошелька
        self._update_economy_balance(user_id, -repay_amount)
        
        em = EmbedBuilder.success(
            title="Платёж Принят!",
            description=f"Вы погасили **{repay_amount:,}** {self.currency_emoji}",
            user=interaction.user,
            fields=[
                ("💵 Оплачено", f"{repay_amount:,} {self.currency_emoji}", True),
                ("💳 Осталось", f"{bank[user_id]['loan']:,} {self.currency_emoji}", True)
            ]
        )
        
        if bank[user_id]["loan"] == 0:
            em.set_footer(text="🎉 Кредит полностью погашен!")
        
        await interaction.response.send_message(embed=em)


async def setup(bot):
    await bot.add_cog(Bank(bot))
