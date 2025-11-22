# stocks.py - Биржа и акции
import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime
from utils.embed_builder import EmbedBuilder, Colors


class Stocks(commands.Cog):
    """Биржа и торговля акциями"""
    
    def __init__(self, bot):
        self.bot = bot
        self.stocks_file = 'stocks.json'
        self.currency_emoji = "💎"
        self._ensure_file()
        self.update_prices.start()
    
    def _ensure_file(self):
        if not os.path.exists(self.stocks_file):
            # Начальные компании
            initial_data = {
                "companies": {
                    "TECH": {"name": "TechCorp", "price": 100, "change": 0},
                    "FOOD": {"name": "FoodChain", "price": 50, "change": 0},
                    "GAME": {"name": "GameDev", "price": 75, "change": 0},
                    "CRYPTO": {"name": "CryptoEx", "price": 150, "change": 0},
                    "ENERGY": {"name": "PowerCo", "price": 120, "change": 0}
                },
                "portfolios": {}
            }
            with open(self.stocks_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=4)
    
    def _load_stocks(self):
        with open(self.stocks_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_stocks(self, data):
        with open(self.stocks_file, 'w', encoding='utf-8') as f:
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
            economy_cog._add_transaction(user_id, "stocks", amount, "Биржевая транзакция")
    
    @tasks.loop(hours=1)
    async def update_prices(self):
        """Обновление цен каждый час"""
        data = self._load_stocks()
        for ticker, company in data["companies"].items():
            change_percent = random.uniform(-15, 15)
            old_price = company["price"]
            new_price = int(old_price * (1 + change_percent / 100))
            new_price = max(10, new_price)  # min price
            company["price"] = new_price
            company["change"] = round(((new_price - old_price) / old_price) * 100, 2)
        self._save_stocks(data)
    
    @update_prices.before_loop
    async def before_update_prices(self):
        await self.bot.wait_until_ready()
    
    @app_commands.command(name="stocks", description="📈 Просмотр текущих цен акций")
    async def stocks_list(self, interaction: discord.Interaction):
        data = self._load_stocks()
        companies = data["companies"]
        
        fields = []
        for ticker, info in companies.items():
            change_emoji = "📈" if info["change"] >= 0 else "📉"
            change_color = "+" if info["change"] >= 0 else ""
            fields.append((
                f"{ticker} - {info['name']}",
                f"Цена: **{info['price']:,}**{self.currency_emoji}\n{change_emoji} {change_color}{info['change']}%",
                True
            ))
        
        em = EmbedBuilder.info(
            title="Биржа Акций",
            description="Текущие цены акций (обновляются каждый час)",
            user=interaction.user,
            fields=fields
        )
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="stock-buy", description="💰 Купить акции")
    @app_commands.describe(ticker="Тикер компании (TECH, FOOD и т.д.)", amount="Количество акций")
    async def stock_buy(self, interaction: discord.Interaction, ticker: str, amount: int):
        ticker = ticker.upper()
        if amount <= 0:
            await interaction.response.send_message("❌ Количество должно быть больше 0!", ephemeral=True)
            return
        
        data = self._load_stocks()
        if ticker not in data["companies"]:
            await interaction.response.send_message(f"❌ Компания {ticker} не найдена!", ephemeral=True)
            return
        
        price = data["companies"][ticker]["price"]
        total_cost = price * amount
        user_id = str(interaction.user.id)
        balance = self._get_economy_balance(user_id)
        
        if balance < total_cost:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"Нужно: **{total_cost:,}**{self.currency_emoji}\nУ вас: **{balance:,}**{self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Покупка
        if user_id not in data["portfolios"]:
            data["portfolios"][user_id] = {}
        if ticker not in data["portfolios"][user_id]:
            data["portfolios"][user_id][ticker] = 0
        data["portfolios"][user_id][ticker] += amount
        self._save_stocks(data)
        self._update_economy_balance(user_id, -total_cost)
        
        em = EmbedBuilder.success(
            title="Акции Куплены!",
            description=f"Вы купили **{amount}** акций **{ticker}**",
            user=interaction.user,
            fields=[
                ("Цена за акцию", f"{price:,}{self.currency_emoji}", True),
                ("Итого", f"{total_cost:,}{self.currency_emoji}", True),
                ("Теперь у вас", f"{data['portfolios'][user_id][ticker]} акций {ticker}", False)
            ]
        )
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="stock-sell", description="💸 Продать акции")
    @app_commands.describe(ticker="Тикер компании", amount="Количество акций")
    async def stock_sell(self, interaction: discord.Interaction, ticker: str, amount: int):
        ticker = ticker.upper()
        user_id = str(interaction.user.id)
        data = self._load_stocks()
        
        if user_id not in data["portfolios"] or ticker not in data["portfolios"][user_id]:
            await interaction.response.send_message(f"❌ У вас нет акций {ticker}!", ephemeral=True)
            return
        
        owned = data["portfolios"][user_id][ticker]
        if amount > owned:
            await interaction.response.send_message(f"❌ У вас только {owned} акций {ticker}!", ephemeral=True)
            return
        
        price = data["companies"][ticker]["price"]
        total_revenue = price * amount
        
        # Продажа
        data["portfolios"][user_id][ticker] -= amount
        if data["portfolios"][user_id][ticker] == 0:
            del data["portfolios"][user_id][ticker]
        self._save_stocks(data)
        self._update_economy_balance(user_id, total_revenue)
        
        em = EmbedBuilder.success(
            title="Акции Проданы!",
            description=f"Вы продали **{amount}** акций **{ticker}**",
            user=interaction.user,
            fields=[
                ("Цена за акцию", f"{price:,}{self.currency_emoji}", True),
                ("Получено", f"+{total_revenue:,}{self.currency_emoji}", True)
            ]
        )
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="portfolio", description="💼 Ваш портфель акций")
    async def portfolio(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = self._load_stocks()
        
        if user_id not in data["portfolios"] or not data["portfolios"][user_id]:
            em = EmbedBuilder.info(
                title="Портфель Пуст",
                description="У вас пока нет акций. Используйте `/stock-buy` для покупки!",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        fields = []
        total_value = 0
        for ticker, amount in data["portfolios"][user_id].items():
            price = data["companies"][ticker]["price"]
            value = price * amount
            total_value += value
            fields.append((
                f"{ticker} ({data['companies'][ticker]['name']})",
                f"Акций: **{amount}**\nЦена: {price:,}{self.currency_emoji}\nСтоимость: **{value:,}**{self.currency_emoji}",
                True
            ))
        
        fields.append(("💎 Общая стоимость портфеля", f"**{total_value:,}**{self.currency_emoji}", False))
        
        em = EmbedBuilder.economy(
            title="Ваш Портфель Акций",
            description=f"Портфель {interaction.user.display_name}",
            user=interaction.user,
            fields=fields
        )
        await interaction.response.send_message(embed=em)


async def setup(bot):
    await bot.add_cog(Stocks(bot))
