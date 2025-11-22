# games.py - Дополнительные игры
"""Новые игры: Blackjack, Poker, Dice"""
import discord
from discord import app_commands
from discord.ext import commands
import random
from typing import List
from utils.embed_builder import EmbedBuilder, Colors


class BlackjackView(discord.ui.View):
    """Интерактивная игра в блэкджек"""
    
    def __init__(self, game_cog, player, bet, dealer_hand, player_hand):
        super().__init__(timeout=60)
        self.game_cog = game_cog
        self.player = player
        self.bet = bet
        self.dealer_hand = dealer_hand
        self.player_hand = player_hand
        self.finished = False
    
    def calculate_hand(self, hand: List[str]) -> int:
        """Подсчитать стоимость руки"""
        total = 0
        aces = 0
        
        for card in hand:
            if card in ['J', 'Q', 'K']:
                total += 10
            elif card == 'A':
                aces += 1
                total += 11
            else:
                total += int(card)
        
        # Обрабатываем тузы
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total
    
    def hand_to_string(self, hand: List[str]) -> str:
        """Форматирование руки для отображения"""
        return " ".join([f"**{card}**" for card in hand])
    
    async def update_game_embed(self, interaction: discord.Interaction, final=False):
        """Обновить embed игры"""
        player_total = self.calculate_hand(self.player_hand)
        
        if final:
            dealer_total = self.calculate_hand(self.dealer_hand)
            dealer_cards = self.hand_to_string(self.dealer_hand)
            
            # Определение победителя
            result = ""
            winnings = 0
            
            if player_total > 21:
                result = "❌ Перебор! Вы проиграли"
                winnings = -self.bet
                title_color = Colors.GAME_LOSS
            elif dealer_total > 21:
                result = "✅ Дилер перебрал! Вы выиграли"
                winnings = self.bet
                title_color = Colors.GAME_WIN
            elif player_total > dealer_total:
                result = "✅ Вы выиграли!"
                # Блэкджек = 21 с двух карт
                if len(self.player_hand) == 2 and player_total == 21:
                    winnings = int(self.bet * 1.5)
                    result += " 🎉 БЛЭКДЖЕК!"
                else:
                    winnings = self.bet
                title_color = Colors.GAME_WIN
            elif player_total < dealer_total:
                result = "❌ Дилер выиграл!"
                winnings = -self.bet
                title_color = Colors.GAME_LOSS
            else:
                result = "🤝 Ничья"
                winnings = 0
                title_color = Colors.PRIMARY
            
            # Обновляем баланс
            user_id = str(self.player.id)
            self.game_cog._update_economy_balance(user_id, winnings)
            
            # Логирование
            if winnings != 0:
                logs_cog = self.game_cog.bot.get_cog('Logs')
                if logs_cog and interaction.guild:
                    await logs_cog.log_game_result(
                        guild=interaction.guild,
                        user=self.player,
                        game_name="Blackjack",
                        is_win=winnings > 0,
                        bet=self.bet,
                        result=winnings
                    )
            
            em = discord.Embed(
                title=f"🃏 Blackjack - {result}",
                description=f"**Ваша рука:** {self.hand_to_string(self.player_hand)} = **{player_total}**\n"
                           f"**Рука дилера:** {dealer_cards} = **{dealer_total}**\n\n"
                           f"**Изменение:** {winnings:+,}💎",
                color=title_color,
                timestamp=discord.utils.utcnow()
            )
        else:
            # Показываем только одну карту дилера
            dealer_cards = f"**{self.dealer_hand[0]}** ❓"
            
            em = discord.Embed(
                title="🃏 Blackjack",
                description=f"**Ваша рука:** {self.hand_to_string(self.player_hand)} = **{player_total}**\n"
                           f"**Рука дилера:** {dealer_cards}\n\n"
                           f"**Ставка:** {self.bet:,}💎",
                color=Colors.PRIMARY
            )
        
        em.set_footer(text=f"Игрок: {self.player.display_name}", icon_url=self.player.display_avatar.url)
        return em
    
    @discord.ui.button(label="Hit (Взять карту)", style=discord.ButtonStyle.primary, emoji="➕")
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        # Берём карту
        deck = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.player_hand.append(random.choice(deck))
        
        player_total = self.calculate_hand(self.player_hand)
        
        if player_total > 21:
            # Перебор - игра закончена
            self.finished = True
            for item in self.children:
                item.disabled = True
            em = await self.update_game_embed(interaction, final=True)
            await interaction.response.edit_message(embed=em, view=self)
        else:
            em = await self.update_game_embed(interaction, final=False)
            await interaction.response.edit_message(embed=em, view=self)
    
    @discord.ui.button(label="Stand (Остановиться)", style=discord.ButtonStyle.success, emoji="✋")
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        # Дилер берёт карты до 17
        deck = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        while self.calculate_hand(self.dealer_hand) < 17:
            self.dealer_hand.append(random.choice(deck))
        
        self.finished = True
        for item in self.children:
            item.disabled = True
        
        em = await self.update_game_embed(interaction, final=True)
        await interaction.response.edit_message(embed=em, view=self)
    
    @discord.ui.button(label="Double (Удвоить)", style=discord.ButtonStyle.danger, emoji="✖️")
    async def double_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        # Можно удвоить только с 2 картами
        if len(self.player_hand) != 2:
            await interaction.response.send_message("❌ Удвоить можно только с двумя картами!", ephemeral=True)
            return
        
        user_id = str(self.player.id)
        balance = self.game_cog._get_economy_balance(user_id)
        
        if balance < self.bet:
            await interaction.response.send_message("❌ Недостаточно средств для удвоения!", ephemeral=True)
            return
        
        # Удваиваем ставку
        self.bet *= 2
        
        # Берём одну карту и сразу стоп
        deck = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.player_hand.append(random.choice(deck))
        
        # Дилер берёт карты
        while self.calculate_hand(self.dealer_hand) < 17:
            self.dealer_hand.append(random.choice(deck))
        
        self.finished = True
        for item in self.children:
            item.disabled = True
        
        em = await self.update_game_embed(interaction, final=True)
        await interaction.response.edit_message(embed=em, view=self)


class Games(commands.Cog):
    """Дополнительные игры"""
    
    def __init__(self, bot):
        self.bot = bot
        self.currency_emoji = "💎"
    
    def _get_economy_balance(self, user_id: str) -> int:
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            return economy_cog._get_user_data(user_id).get('balance', 0)
        return 0
    
    def _update_economy_balance(self, user_id: str, amount: int):
        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            economy_cog._update_balance(user_id, amount)
            economy_cog._add_transaction(user_id, "game", amount, "Результат игры")
    
    @app_commands.command(name="blackjack", description="🃏 Сыграть в блэкджек")
    @app_commands.describe(bet="Ставка (минимум 10 крионов)")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        """Игра в блэкджек против дилера"""
        if bet < 10:
            await interaction.response.send_message("❌ Минимальная ставка 10 крионов!", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        balance = self._get_economy_balance(user_id)
        
        if balance < bet:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"У вас: **{balance:,}**{self.currency_emoji}\nНужно: **{bet:,}**{self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Снимаем ставку
        self._update_economy_balance(user_id, -bet)
        
        # Раздаём карты
        deck = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        player_hand = [random.choice(deck), random.choice(deck)]
        dealer_hand = [random.choice(deck), random.choice(deck)]
        
        # Создаём игру
        view = BlackjackView(self, interaction.user, bet, dealer_hand, player_hand)
        em = await view.update_game_embed(interaction, final=False)
        
        await interaction.response.send_message(embed=em, view=view)
    
    @app_commands.command(name="poker", description="🎴 Сыграть в покер (5 карт)")
    @app_commands.describe(bet="Ставка (минимум 20 крионов)")
    async def poker(self, interaction: discord.Interaction, bet: int):
        """Упрощённый покер с 5 картами"""
        if bet < 20:
            await interaction.response.send_message("❌ Минимальная ставка 20 крионов!", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        balance = self._get_economy_balance(user_id)
        
        if balance < bet:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"У вас: **{balance:,}**{self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Раздаём 5 карт
        cards = []
        suits = ['♠️', '♥️', '♣️', '♦️']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        
        for _ in range(5):
            cards.append(f"{random.choice(ranks)}{random.choice(suits)}")
        
        # Анализ комбинаций
        rank_values = [c[:-2] if len(c) == 3 else c[:-1] for c in cards]
        rank_counts = {}
        for r in rank_values:
            rank_counts[r] = rank_counts.get(r, 0) + 1
        
        counts = sorted(rank_counts.values(), reverse=True)
        
        # Определяем комбинацию
        if counts == [5]:
            combo = "Невозможно!"
            mult = 0
        elif counts == [4, 1]:
            combo = "Каре"
            mult = 25
        elif counts == [3, 2]:
            combo = "Фулл-хаус"
            mult = 10
        elif counts == [3, 1, 1]:
            combo = "Тройка"
            mult = 3
        elif counts == [2, 2, 1]:
            combo = "Две пары"
            mult = 2
        elif counts == [2, 1, 1, 1]:
            combo = "Пара"
            mult = 1
        else:
            combo = "Старшая карта"
            mult = 0
        
        winnings = bet * mult
        result = winnings - bet
        
        # Обновляем баланс
        self._update_economy_balance(user_id, result)
        
        # Логирование
        logs_cog = self.bot.get_cog('Logs')
        if logs_cog and interaction.guild:
            await logs_cog.log_game_result(
                guild=interaction.guild,
                user=interaction.user,
                game_name="Poker",
                is_win=result > 0,
                bet=bet,
                result=result
            )
        
        color = Colors.GAME_WIN if result > 0 else Colors.GAME_LOSS if result < 0 else Colors.PRIMARY
        
        em = discord.Embed(
            title=f"🎴 Покер - {combo}",
            description=f"**Ваши карты:** {' '.join(cards)}\n\n"
                       f"**Комбинация:** {combo} (x{mult})\n"
                       f"**Изменение:** {result:+,}{self.currency_emoji}",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        em.set_footer(text=f"Игрок: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="dice", description="🎲 Угадать сумму двух кубиков")
    @app_commands.describe(
        bet="Ставка (минимум 10 крионов)",
        guess="Ваша ставка (2-12)"
    )
    async def dice(self, interaction: discord.Interaction, bet: int, guess: int):
        """Игра в кости - угадать сумму двух кубиков"""
        if bet < 10:
            await interaction.response.send_message("❌ Минимальная ставка 10 крионов!", ephemeral=True)
            return
        
        if guess < 2 or guess > 12:
            await interaction.response.send_message("❌ Guess должен быть от 2 до 12!", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        balance = self._get_economy_balance(user_id)
        
        if balance < bet:
            em = EmbedBuilder.error(
                title="Недостаточно средств!",
                description=f"У вас: **{balance:,}**{self.currency_emoji}",
                user=interaction.user
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Бросаем кубики
        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)
        total = die1 + die2
        
        # Определяем выигрыш
        diff = abs(guess - total)
        
        if diff == 0:
            # Точное попадание
            mult = 10
            result_text = "🎯 Точное попадание!"
        elif diff == 1:
            # Близко
            mult = 3
            result_text = "👍 Близко!"
        elif diff == 2:
            # Почти
            mult = 1.5
            result_text = "😊 Почти!"
        else:
            # Промах
            mult = 0
            result_text = "❌ Промах!"
        
        winnings = int(bet * mult)
        result = winnings - bet
        
        # Обновляем баланс
        self._update_economy_balance(user_id, result)
        
        # Логирование
        logs_cog = self.bot.get_cog('Logs')
        if logs_cog and interaction.guild:
            await logs_cog.log_game_result(
                guild=interaction.guild,
                user=interaction.user,
                game_name="Dice",
                is_win=result > 0,
                bet=bet,
                result=result
            )
        
        color = Colors.GAME_WIN if result > 0 else Colors.GAME_LOSS if result < 0 else Colors.PRIMARY
        
        em = discord.Embed(
            title=f"🎲 Кости - {result_text}",
            description=f"**Кубики:** 🎲 {die1} + 🎲 {die2} = **{total}**\n"
                       f"**Ваша ставка:** {guess}\n"
                       f"**Множитель:** x{mult}\n\n"
                       f"**Изменение:** {result:+,}{self.currency_emoji}",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        em.set_footer(text=f"Игрок: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=em)


async def setup(bot):
    await bot.add_cog(Games(bot))
