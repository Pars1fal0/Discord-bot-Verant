# embed_builder.py
"""Утилита для создания красивых embeds с единым стилем"""
import discord
from datetime import datetime
from typing import Optional, List, Tuple


class Colors:
    """Холодная синяя палитра для embeds"""
    # Основные цвета
    PRIMARY = 0x5865F2      # Синий - основной
    ACCENT = 0x00D9FF       # Голубой - акценты
    SUCCESS = 0x1ABC9C      # Бирюзовый - успех
    PREMIUM = 0x7289DA      # Фиолетовый - премиум
    DARK = 0x2C2F33         # Тёмно-синий - фон
    
    # Специальные
    ERROR = 0x5865F2        # Синий даже для ошибок (холодная палитра)
    WARNING = 0x7289DA      # Фиолетовый для предупреждений
    INFO = 0x00D9FF         # Голубой для информации
    
    # Игры и действия
    GAME_WIN = 0x1ABC9C     # Бирюзовый - выигрыш
    GAME_LOSS = 0x5865F2    # Синий - проигрыш
    ECONOMY = 0x00D9FF      # Голубой - экономика
    LEVEL = 0x7289DA        # Фиолетовый - уровни


class EmbedBuilder:
    """
    Класс для создания красивых embeds с единым стилем.
    Использует холодную синюю палитру.
    """
    
    @staticmethod
    def create_base(
        title: str,
        description: str = None,
        color: int = Colors.PRIMARY,
        thumbnail: str = None,
        image: str = None
    ) -> discord.Embed:
        """
        Создать базовый embed с применением стиля
        
        Args:
            title: Заголовок
            description: Описание
            color: Цвет (из Colors)
            thumbnail: URL миниатюры
            image: URL изображения
            
        Returns:
            Настроенный Embed
        """
        em = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        
        if thumbnail:
            em.set_thumbnail(url=thumbnail)
        if image:
            em.set_image(url=image)
            
        return em
    
    @staticmethod
    def success(
        title: str,
        description: str,
        user: discord.User = None,
        fields: List[Tuple[str, str, bool]] = None
    ) -> discord.Embed:
        """
        Создать embed успеха (бирюзовый)
        
        Args:
            title: Заголовок
            description: Описание
            user: Пользователь для footer
            fields: Список полей [(name, value, inline), ...]
        """
        em = EmbedBuilder.create_base(
            title=f"✅ {title}",
            description=description,
            color=Colors.SUCCESS,
            thumbnail=user.display_avatar.url if user else None
        )
        
        if fields:
            for name, value, inline in fields:
                em.add_field(name=name, value=value, inline=inline)
        
        if user:
            em.set_footer(
                text=f"Запрос от {user.display_name}",
                icon_url=user.display_avatar.url
            )
        
        return em
    
    @staticmethod
    def error(
        title: str,
        description: str,
        user: discord.User = None
    ) -> discord.Embed:
        """Создать embed ошибки (синий, холодная палитра)"""
        em = EmbedBuilder.create_base(
            title=f"❌ {title}",
            description=description,
            color=Colors.ERROR
        )
        
        if user:
            em.set_footer(
                text=f"Запрос от {user.display_name}",
                icon_url=user.display_avatar.url
            )
        
        return em
    
    @staticmethod
    def info(
        title: str,
        description: str,
        user: discord.User = None,
        fields: List[Tuple[str, str, bool]] = None,
        thumbnail: str = None
    ) -> discord.Embed:
        """Создать информационный embed (голубой)"""
        em = EmbedBuilder.create_base(
            title=f"ℹ️ {title}",
            description=description,
            color=Colors.INFO,
            thumbnail=thumbnail or (user.display_avatar.url if user else None)
        )
        
        if fields:
            for name, value, inline in fields:
                em.add_field(name=name, value=value, inline=inline)
        
        if user:
            em.set_footer(
                text=f"Запрос от {user.display_name}",
                icon_url=user.display_avatar.url
            )
        
        return em
    
    @staticmethod
    def warning(
        title: str,
        description: str,
        user: discord.User = None
    ) -> discord.Embed:
        """Создать embed предупреждения (фиолетовый)"""
        em = EmbedBuilder.create_base(
            title=f"⚠️ {title}",
            description=description,
            color=Colors.WARNING
        )
        
        if user:
            em.set_footer(
                text=f"Запрос от {user.display_name}",
                icon_url=user.display_avatar.url
            )
        
        return em
    
    @staticmethod
    def economy(
        title: str,
        description: str,
        user: discord.User,
        fields: List[Tuple[str, str, bool]] = None,
        footer_text: str = None
    ) -> discord.Embed:
        """Создать embed для экономики (голубой)"""
        em = EmbedBuilder.create_base(
            title=title,
            description=description,
            color=Colors.ECONOMY,
            thumbnail=user.display_avatar.url
        )
        
        if fields:
            for name, value, inline in fields:
                em.add_field(name=name, value=value, inline=inline)
        
        if footer_text:
            em.set_footer(text=footer_text, icon_url=user.display_avatar.url)
        else:
            em.set_footer(
                text=f"Запрос от {user.display_name}",
                icon_url=user.display_avatar.url
            )
        
        return em
    
    @staticmethod
    def level(
        title: str,
        description: str,
        user: discord.User,
        fields: List[Tuple[str, str, bool]] = None,
        footer_text: str = None
    ) -> discord.Embed:
        """Создать embed для уровней (фиолетовый)"""
        em = EmbedBuilder.create_base(
            title=title,
            description=description,
            color=Colors.LEVEL,
            thumbnail=user.display_avatar.url
        )
        
        if fields:
            for name, value, inline in fields:
                em.add_field(name=name, value=value, inline=inline)
        
        if footer_text:
            em.set_footer(text=footer_text, icon_url=user.display_avatar.url)
        else:
            em.set_footer(
                text=f"Запрос от {user.display_name}",
                icon_url=user.display_avatar.url
            )
        
        return em
    
    @staticmethod
    def game_result(
        title: str,
        description: str,
        is_win: bool,
        user: discord.User,
        fields: List[Tuple[str, str, bool]] = None
    ) -> discord.Embed:
        """
        Создать embed для результата игры
        
        Args:
            title: Заголовок
            description: Описание
            is_win: True если выигрыш, False если проигрыш
            user: Пользователь
            fields: Поля для добавления
        """
        color = Colors.GAME_WIN if is_win else Colors.GAME_LOSS
        
        em = EmbedBuilder.create_base(
            title=title,
            description=description,
            color=color,
            thumbnail=user.display_avatar.url
        )
        
        if fields:
            for name, value, inline in fields:
                em.add_field(name=name, value=value, inline=inline)
        
        em.set_footer(
            text=f"Запрос от {user.display_name}",
            icon_url=user.display_avatar.url
        )
        
        return em
    
    @staticmethod
    def leaderboard(
        title: str,
        description: str,
        entries: List[Tuple[str, str]],
        user: discord.User = None,
        color: int = Colors.PREMIUM
    ) -> discord.Embed:
        """
        Создать embed для таблицы лидеров
        
        Args:
            title: Заголовок
            description: Описание
            entries: Список записей [(name, value), ...]
            user: Пользователь для footer
            color: Цвет embed
        """
        em = EmbedBuilder.create_base(
            title=title,
            description=description,
            color=color
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, (name, value) in enumerate(entries):
            medal = medals[idx] if idx < 3 else f"`{idx + 1}.`"
            em.add_field(
                name=f"{medal} {name}",
                value=value,
                inline=False
            )
        
        if user:
            em.set_footer(
                text=f"Запрос от {user.display_name}",
                icon_url=user.display_avatar.url
            )
        
        return em
    
    @staticmethod
    def admin(
        title: str,
        description: str,
        admin: discord.User,
        fields: List[Tuple[str, str, bool]] = None
    ) -> discord.Embed:
        """Создать embed для админских действий (основной синий)"""
        em = EmbedBuilder.create_base(
            title=f"⚙️ {title}",
            description=description,
            color=Colors.PRIMARY
        )
        
        if fields:
            for name, value, inline in fields:
                em.add_field(name=name, value=value, inline=inline)
        
        em.set_footer(
            text=f"Администратор: {admin.display_name}",
            icon_url=admin.display_avatar.url
        )
        
        return em
    
    @staticmethod
    def create_progress_bar(current: int, maximum: int, length: int = 15) -> str:
        """
        Создать прогресс-бар
        
        Args:
            current: Текущее значение
            maximum: Максимальное значение
            length: Длина бара
            
        Returns:
            Строка прогресс-бара
        """
        if maximum == 0:
            return "░" * length
        
        filled = int((current / maximum) * length)
        filled = max(0, min(filled, length))
        
        return "▓" * filled + "░" * (length - filled)
    
    @staticmethod
    def format_number(number: int) -> str:
        """Форматировать число с разделителями"""
        return f"{number:,}"
