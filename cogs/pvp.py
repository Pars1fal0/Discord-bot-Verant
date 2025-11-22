# pvp.py - PvP Дуэли
"""Система дуэлей между игроками"""
import discord
from discord import app_commands
from discord.ext import commands
import random
from typing import Optional
from utils.embed_builder import EmbedBuilder, Colors


class DuelView(discord.ui.View):
    """View для управления дуэлью"""
    
    def __init__(self, pvp_cog, challenger, opponent, bet):
        super().__init__(timeout=60)
        self.pvp_cog = pvp_cog
        self.challenger = challenger
        self.opponent = opponent
        self.bet = bet
        self.accepted = False
    
    @discord.ui.button(label="Принять вызов", style=discord.ButtonStyle.success, emoji="⚔️")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("❌ Это не ваша дуэль!", ephemeral=True)
            return
        
        # Проверяем баланс оппонента
        opponent_balance = self.pvp_cog._get_economy_balance(str(self.opponent.id))
        if opponent_balance < self.bet:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"Для участия в дуэли нужно **{self.bet:,}**💎",
                user=self.opponent
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Отключаем кнопки
        for item in self.children:
            item.disabled = True
        
        # Проводим дуэль
        winner, result_text = self.pvp_cog._conduct_duel(self.challenger, self.opponent)
        
        # Начисляем/снимаем деньги
        if winner == self.challenger:
            self.pvp_cog._update_economy_balance(str(self.challenger.id), self.bet)
            self.pvp_cog._update_economy_balance(str(self.opponent.id), -self.bet)
            winner_mention = self.challenger.mention
            loser_mention = self.opponent.mention
        else:
            self.pvp_cog._update_economy_balance(str(self.challenger.id), -self.bet)
            self.pvp_cog._update_economy_balance(str(self.opponent.id), self.bet)
            winner_mention = self.opponent.mention
            loser_mention = self.challenger.mention
        
        # Обновляем статистику
        self.pvp_cog._update_stats(str(winner.id), win=True)
        loser = self.opponent if winner == self.challenger else self.challenger
        self.pvp_cog._update_stats(str(loser.id), win=False)
        
        # Результат
        em = discord.Embed(
            title="⚔️ Результат Дуэли",
            description=f"{result_text}\n\n"
                       f"**Победитель:** {winner_mention}\n"
                       f"**Проигравший:** {loser_mention}",
            color=Colors.SUCCESS,
            timestamp=discord.utils.utcnow()
        )
        em.add_field(name="Ставка", value=f"{self.bet:,}💎", inline=True)
        em.add_field(name="Выигрыш", value=f"+{self.bet:,}💎", inline=True)
        em.set_thumbnail(url=winner.display_avatar.url)
        em.set_footer(text=f"Победитель: {winner.display_name}")
        
        # Логирование
        logs_cog = self.pvp_cog.bot.get_cog('Logs')
        if logs_cog and interaction.guild:
            await logs_cog.log_game_result(
                guild=interaction.guild,
                user=winner,
                game_name="PvP Дуэль",
                is_win=True,
                bet=self.bet,
                result=self.bet
            )
        
        await interaction.response.edit_message(embed=em, view=self)
    
    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("❌ Это не ваша дуэль!", ephemeral=True)
            return
        
        # Отключаем кнопки
        for item in self.children:
            item.disabled = True
        
        em = discord.Embed(
            title="❌ Вызов Отклонён",
            description=f"{self.opponent.mention} отклонил вызов на дуэль от {self.challenger.mention}",
            color=Colors.ERROR
        )
        
        await interaction.response.edit_message(embed=em, view=self)


class PVP(commands.Cog):
    """Система PvP дуэлей"""
    
    def __init__(self, bot):
        self.bot = bot
        self.currency_emoji = "💎"
        self.pvp_stats_file = 'pvp_stats.json'
        self._ensure_stats_file()
    
    def _ensure_stats_file(self):
        """Создать файл статистики если его нет"""
        import os
        import json
        if not os.path.exists(self.pvp_stats_file):
            with open(self.pvp_stats_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
    
    def _load_stats(self):
        """Загрузить статистику"""
        import json
        with open(self.pvp_stats_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_stats(self, data):
        """Сохранить статистику"""
        import json
        with open(self.pvp_stats_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def _update_stats(self, user_id: str, win: bool):
        """Обновить статистику пользователя"""
        stats = self._load_stats()
        if user_id not in stats:
            stats[user_id] = {"wins": 0, "losses": 0}
        
        if win:
            stats[user_id]["wins"] += 1
        else:
            stats[user_id]["losses"] += 1
        
        self._save_stats(stats)
    
    def _get_economy_balance(self, user_id: str) -> int:
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            return economy_cog._get_user_data(user_id).get('balance', 0)
        return 0
    
    def _update_economy_balance(self, user_id: str, amount: int):
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            economy_cog._update_balance(user_id, amount)
            economy_cog._add_transaction(user_id, "pvp", amount, "PvP дуэль")
    
    def _conduct_duel(self, player1: discord.Member, player2: discord.Member):
        """Провести дуэль и определить победителя"""
        # Параметры: сила, ловкость, удача
        p1_power = random.randint(1, 100)
        p1_agility = random.randint(1, 100)
        p1_luck = random.randint(1, 50)
        
        p2_power = random.randint(1, 100)
        p2_agility = random.randint(1, 100)
        p2_luck = random.randint(1, 50)
        
        p1_total = p1_power + p1_agility + p1_luck
        p2_total = p2_power + p2_agility + p2_luck
        
        if p1_total > p2_total:
            winner = player1
            result_text = (
                f"**💪 Сила:** {p1_power} vs {p2_power}\n"
                f"**🏃 Ловкость:** {p1_agility} vs {p2_agility}\n"
                f"**🍀 Удача:** {p1_luck} vs {p2_luck}\n\n"
                f"**📊 Итого:** {p1_total} vs {p2_total}"
            )
        else:
            winner = player2
            result_text = (
                f"**💪 Сила:** {p2_power} vs {p1_power}\n"
                f"**🏃 Ловкость:** {p2_agility} vs {p1_agility}\n"
                f"**🍀 Удача:** {p2_luck} vs {p1_luck}\n\n"
                f"**📊 Итого:** {p2_total} vs {p1_total}"
            )
        
        return winner, result_text
    
    @app_commands.command(name="duel", description="⚔️ Вызвать на дуэль")
    @app_commands.describe(
        opponent="Противник",
        bet="Ставка (минимум 100 крионов)"
    )
    async def duel(self, interaction: discord.Interaction, opponent: discord.Member, bet: int):
        """Вызвать пользователя на дуэль"""
        challenger_id = str(interaction.user.id)
        opponent_id = str(opponent.id)
        
        # Проверки
        if bet < 100:
            await interaction.response.send_message("❌ Минимальная ставка 100 крионов!", ephemeral=True)
            return
        
        if opponent.bot:
            await interaction.response.send_message("❌ Нельзя вызвать бота на дуэль!", ephemeral=True)
            return
        
        if challenger_id == opponent_id:
            await interaction.response.send_message("❌ Нельзя вызвать самого себя!", ephemeral=True)
            return
        
        # Проверка баланса вызывающего
        challenger_balance = self._get_economy_balance(challenger_id)
        if challenger_balance < bet:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"У вас: **{challenger_balance:,}**{self.currency_emoji}\nНужно: **{bet:,}**{self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Создаём вызов
        view = DuelView(self, interaction.user, opponent, bet)
        
        em = discord.Embed(
            title="⚔️ Вызов на Дуэль!",
            description=f"{interaction.user.mention} вызывает {opponent.mention} на дуэль!",
            color=Colors.PRIMARY
        )
        em.add_field(name="Ставка", value=f"{bet:,}{self.currency_emoji}", inline=True)
        em.add_field(name="Правила", value="Победитель забирает ставку проигравшего", inline=False)
        em.set_footer(text=f"У {opponent.display_name} есть 60 секунд чтобы принять вызов")
        
        await interaction.response.send_message(embed=em, view=view)
    
    @app_commands.command(name="pvp-stats", description="📊 Статистика PvP")
    @app_commands.describe(user="Пользователь (по умолчанию - вы)")
    async def pvp_stats(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Показать PvP статистику"""
        target = user or interaction.user
        user_id = str(target.id)
        
        stats = self._load_stats()
        user_stats = stats.get(user_id, {"wins": 0, "losses": 0})
        
        wins = user_stats["wins"]
        losses = user_stats["losses"]
        total = wins + losses
        
        if total > 0:
            winrate = (wins / total) * 100
        else:
            winrate = 0
        
        # Ранг на основе побед
        if wins >= 100:
            rank = "🏆 Легенда"
        elif wins >= 50:
            rank = "💎 Мастер"
        elif wins >= 25:
            rank = "⚔️ Эксперт"
        elif wins >= 10:
            rank = "🛡️ Воин"
        elif wins >= 5:
            rank = "🗡️ Боец"
        else:
            rank = "👤 Новичок"
        
        em = EmbedBuilder.info(
            title=f"📊 PvP Статистика - {target.display_name}",
            description=f"**Ранг:** {rank}",
            user=target,
            fields=[
                ("✅ Победы", str(wins), True),
                ("❌ Поражения", str(losses), True),
                ("📈 Процент побед", f"{winrate:.1f}%", True),
                ("🎯 Всего дуэлей", str(total), True)
            ]
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="pvp-leaderboard", description="🏆 Топ PvP игроков")
    async def pvp_leaderboard(self, interaction: discord.Interaction):
        """Таблица лидеров PvP"""
        stats = self._load_stats()
        
        if not stats:
            em = EmbedBuilder.info(
                title="🏆 Топ PvP Игроков",
                description="Пока нет данных о дуэлях!",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em)
            return
        
        # Сортируем по победам
        leaderboard = []
        for user_id, user_stats in stats.items():
            wins = user_stats["wins"]
            losses = user_stats["losses"]
            total = wins + losses
            winrate = (wins / total * 100) if total > 0 else 0
            leaderboard.append((user_id, wins, losses, winrate))
        
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        leaderboard = leaderboard[:10]  # Топ 10
        
        description = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (user_id, wins, losses, winrate) in enumerate(leaderboard, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                medal = medals[i-1] if i <= 3 else f"`{i}.`"
                description += f"{medal} **{user.display_name}** - {wins}W / {losses}L ({winrate:.1f}%)\n"
            except:
                continue
        
        em = discord.Embed(
            title="🏆 Топ PvP Игроков",
            description=description,
            color=Colors.PREMIUM,
            timestamp=discord.utils.utcnow()
        )
        em.set_footer(text="Обновляется в реальном времени")
        
        await interaction.response.send_message(embed=em)


async def setup(bot):
    await bot.add_cog(PVP(bot))
