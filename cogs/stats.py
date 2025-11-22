# stats.py - Расширенная статистика
"""Детальная статистика пользователя и сервера"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from datetime import datetime
from utils.embed_builder import EmbedBuilder, Colors


class Stats(commands.Cog):
    """Система статистики"""
    
    def __init__(self, bot):
        self.bot = bot
        self.currency_emoji = "💎"
    
    @app_commands.command(name="stats", description="📊 Полная статистика пользователя")
    @app_commands.describe(user="Пользователь (по умолчанию - вы)")
    async def user_stats(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Показать полную статистику пользователя"""
        target = user or interaction.user
        user_id = str(target.id)
        
        # Собираем данные из всех когов
        stats_data = {}
        
        # Economy
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            eco_data = economy_cog._get_user_data(user_id)
            stats_data['balance'] = eco_data.get('balance', 0)
            stats_data['total_earned'] = eco_data.get('total_earned', 0)
            stats_data['games_played'] = eco_data.get('games_played', 0)
        
        # Levels
        levels_cog = self.bot.get_cog('Levels')
        if levels_cog:
            level_data = levels_cog._get_user_data(user_id)
            stats_data['level'] = level_data.get('level', 1)
            stats_data['xp'] = level_data.get('xp', 0)
            stats_data['messages'] = level_data.get('messages', 0)
        
        # Bank
        try:
            import json
            with open('bank.json', 'r') as f:
                bank_data = json.load(f)
                if user_id in bank_data:
                    stats_data['deposit'] = bank_data[user_id].get('deposit', 0)
                    stats_data['loan'] = bank_data[user_id].get('loan', 0)
        except:
            stats_data['deposit'] = 0
            stats_data['loan'] = 0
        
        # Business
        try:
            import json
            with open('business.json', 'r') as f:
                business_data = json.load(f)
                stats_data['businesses'] = len(business_data.get(user_id, {}))
        except:
            stats_data['businesses'] = 0
        
        # Stocks
        try:
            import json
            with open('stocks.json', 'r') as f:
                stocks_data = json.load(f)
                portfolios = stocks_data.get('portfolios', {})
                if user_id in portfolios:
                    total_stocks = sum(portfolios[user_id].values())
                    stats_data['stocks'] = total_stocks
                else:
                    stats_data['stocks'] = 0
        except:
            stats_data['stocks'] = 0
        
        # PVP
        try:
            import json
            with open('pvp_stats.json', 'r') as f:
                pvp_data = json.load(f)
                if user_id in pvp_data:
                    stats_data['pvp_wins'] = pvp_data[user_id].get('wins', 0)
                    stats_data['pvp_losses'] = pvp_data[user_id].get('losses', 0)
                else:
                    stats_data['pvp_wins'] = 0
                    stats_data['pvp_losses'] = 0
        except:
            stats_data['pvp_wins'] = 0
            stats_data['pvp_losses'] = 0
        
        # Prestige
        try:
            import json
            with open('enhancements.json', 'r') as f:
                enh_data = json.load(f)
                stats_data['prestige'] = enh_data.get('prestiges', {}).get(user_id, 0)
                stats_data['titles'] = len(enh_data.get('titles', {}).get(user_id, []))
        except:
            stats_data['prestige'] = 0
            stats_data['titles'] = 0
        
        # Рассчитываем общий капитал
        total_wealth = stats_data.get('balance', 0) + stats_data.get('deposit', 0) - stats_data.get('loan', 0)
        
        # Создаём embed
        em = discord.Embed(
            title=f"📊 Статистика - {target.display_name}",
            color=Colors.PRIMARY,
            timestamp=discord.utils.utcnow()
        )
        em.set_thumbnail(url=target.display_avatar.url)
        
        # Общее
        em.add_field(
            name="💎 Финансы",
            value=f"Баланс: **{stats_data.get('balance', 0):,}**{self.currency_emoji}\n"
                  f"Депозит: **{stats_data.get('deposit', 0):,}**{self.currency_emoji}\n"
                  f"Кредит: **{stats_data.get('loan', 0):,}**{self.currency_emoji}\n"
                  f"Капитал: **{total_wealth:,}**{self.currency_emoji}",
            inline=True
        )
        
        em.add_field(
            name="📈 Прогрессия",
            value=f"Уровень: **{stats_data.get('level', 1)}**\n"
                  f"XP: **{stats_data.get('xp', 0):,}**\n"
                  f"Престиж: **{stats_data.get('prestige', 0)}**⭐\n"
                  f"Титулов: **{stats_data.get('titles', 0)}**",
            inline=True
        )
        
        em.add_field(
            name="🏢 Бизнес",
            value=f"Бизнесов: **{stats_data.get('businesses', 0)}**/3\n"
                  f"Акций: **{stats_data.get('stocks', 0)}**\n"
                  f"Сообщений: **{stats_data.get('messages', 0):,}**",
            inline=True
        )
        
        # PVP статистика
        pvp_total = stats_data.get('pvp_wins', 0) + stats_data.get('pvp_losses', 0)
        if pvp_total > 0:
            winrate = (stats_data.get('pvp_wins', 0) / pvp_total) * 100
            em.add_field(
                name="⚔️ PvP",
                value=f"Побед: **{stats_data.get('pvp_wins', 0)}**\n"
                      f"Поражений: **{stats_data.get('pvp_losses', 0)}**\n"
                      f"Винрейт: **{winrate:.1f}%**",
                inline=True
            )
        
        em.set_footer(text=f"Участник с {target.joined_at.strftime('%d.%m.%Y')}")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="server-stats", description="📊 Статистика сервера")
    @app_commands.checks.has_permissions(administrator=True)
    async def server_stats(self, interaction: discord.Interaction):
        """Показать статистику сервера"""
        guild = interaction.guild
        
        # Подсчёт пользователей с data
        economy_cog = self.bot.get_cog('Economy')
        levels_cog = self.bot.get_cog('Levels')
        
        if economy_cog:
            eco_data = economy_cog._load_economy()
            registered_users = len(eco_data)
            total_money = sum(user.get('balance', 0) for user in eco_data.values())
        else:
            registered_users = 0
            total_money = 0
        
        if levels_cog:
            level_data = levels_cog._load_levels()
            total_messages = sum(user.get('messages', 0) for user in level_data.values())
        else:
            total_messages = 0
        
        # Статистика бизнесов
        try:
            import json
            with open('business.json', 'r') as f:
                business_data = json.load(f)
                total_businesses = sum(len(businesses) for businesses in business_data.values())
        except:
            total_businesses = 0
        
        # Статистика турниров
        try:
            import json
            with open('tournaments.json', 'r') as f:
                tourn_data = json.load(f)
                active_tournaments = len(tourn_data.get('active', {}))
                total_tournaments = len(tourn_data.get('history', []))
        except:
            active_tournaments = 0
            total_tournaments = 0
        
        em = discord.Embed(
            title=f"📊 Статистика - {guild.name}",
            description=f"Всего участников: **{guild.member_count}**",
            color=Colors.PRIMARY,
            timestamp=discord.utils.utcnow()
        )
        
        if guild.icon:
            em.set_thumbnail(url=guild.icon.url)
        
        em.add_field(
            name="👥 Активность",
            value=f"Зарег. пользователей: **{registered_users}**\n"
                  f"Всего сообщений: **{total_messages:,}**\n"
                  f"Бустов: **{guild.premium_subscription_count}**",
            inline=True
        )
        
        em.add_field(
            name="💰 Экономика",
            value=f"Всего денег: **{total_money:,}**{self.currency_emoji}\n"
                  f"Бизнесов: **{total_businesses}**\n"
                  f"Средний баланс: **{total_money // max(registered_users, 1):,}**{self.currency_emoji}",
            inline=True
        )
        
        em.add_field(
            name="🏆 Турниры",
            value=f"Активных: **{active_tournaments}**\n"
                  f"Завершено: **{total_tournaments}**",
            inline=True
        )
        
        em.add_field(
            name="📅 Информация",
            value=f"Создан: {guild.created_at.strftime('%d.%m.%Y')}\n"
                  f"Регион: {str(guild.preferred_locale)[:2].upper()}\n"
                  f"Владелец: {guild.owner.mention if guild.owner else 'Неизвестно'}",
            inline=False
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="top-rich", description="💰 Топ богачей сервера")
    async def top_rich(self, interaction: discord.Interaction):
        """Топ 10 самых богатых пользователей"""
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await interaction.response.send_message("❌ Экономика недоступна!", ephemeral=True)
            return
        
        eco_data = economy_cog._load_economy()
        
        # Сортируем по балансу
        leaderboard = sorted(
            eco_data.items(),
            key=lambda x: x[1].get('balance', 0),
            reverse=True
        )[:10]
        
        description = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (user_id, data) in enumerate(leaderboard, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                medal = medals[i-1] if i <= 3 else f"`{i}.`"
                balance = data.get('balance', 0)
                description += f"{medal} **{user.display_name}** - {balance:,}{self.currency_emoji}\n"
            except:
                continue
        
        em = discord.Embed(
            title="💰 Топ Богачей",
            description=description or "Нет данных",
            color=Colors.PREMIUM,
            timestamp=discord.utils.utcnow()
        )
        em.set_footer(text="Рейтинг обновляется в реальном времени")
        
        await interaction.response.send_message(embed=em)


async def setup(bot):
    await bot.add_cog(Stats(bot))
