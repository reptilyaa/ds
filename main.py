from discord.ext.commands import bot
from dotenv import load_dotenv
load_dotenv()

import os
import discord
import logging

import os
import time
import sqlite3
import asyncio          # <-- вот сюда
import discord
from discord import app_commands
from discord.ext import commands


# -------------------- ЛОГИ --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("discord_bot")



intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)







# ---------------------- ЗАЩИТА ОТ "ПРИЛОЖЕНИЕ НЕ ОТВЕЧАЕТ" ----------------------
@bot.before_invoke
async def before_any_command(ctx):
    """Автоматическое отложение всех команд для избежания 'приложение не отвечает'"""
    try:
        if hasattr(ctx, "interaction") and ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.interaction.response.defer(ephemeral=True)
    except Exception as e:
        logging.warning(f"[AGPG WARN] Ошибка при auto-defer: {e}")



# -------------------- ИМПОРТЫ --------------------
import traceback
import discord
from discord.ext import commands
from discord import app_commands


# -------------------- НАСТРОЙКИ --------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)



# -------------------- ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК --------------------
@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    """Глобальный обработчик ошибок для всех slash-команд."""

    if interaction.response.is_done():
        try:
            await interaction.followup.send(
                "⚠️ Произошла небольшая ошибка, попробуй ещё раз.",
                ephemeral=True
            )
        except Exception:
            pass
        return

    if isinstance(error, app_commands.CommandInvokeError):
        original = getattr(error, "original", error)
        if isinstance(original, discord.InteractionResponded):
            return
        elif isinstance(original, asyncio.TimeoutError):
            await interaction.response.send_message("⏰ Команда выполнялась слишком долго.", ephemeral=True)
            return
        elif isinstance(original, discord.HTTPException):
            await interaction.response.send_message("⚠️ Ошибка при выполнении команды Discord API.", ephemeral=True)
            return

    try:
        await interaction.response.send_message("❌ Произошла ошибка при выполнении команды.", ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send("❌ Произошла ошибка при выполнении команды.", ephemeral=True)
    except Exception:
        pass

    print(f"[ERROR] Ошибка в команде {interaction.command}:")
    traceback.print_exception(type(error), error, error.__traceback__)




ROLE_PLAYSTATION = "AGPG 🚘"
ROLE_PC = "Гость 🎩"

ROLE_PS4 = "PS4 player"
ROLE_PS5 = "PS5 player"

INITIAL_ROLE = "Новая роль"
REMOVE_ROLE = "New player 👋"

ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID", 0))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
ALLOWED_GUILD_ID = int(os.getenv("ALLOWED_GUILD_ID", 0))
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", 0))

DB_PATH = "applications.db"
# -------------------- БАЗА ДАННЫХ ЗАЯВОК --------------------
import os
import sqlite3
from datetime import datetime, timezone, timedelta
import discord
from typing import Optional

# Московское время
MSK = timezone(timedelta(hours=3))

# Файл базы создаётся рядом с bot.py
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "applications.db")


def init_db():
    """Создаёт таблицу заявок, если она отсутствует"""
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                nickname TEXT,
                platform TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    print("✅ Таблица 'applications' проверена или создана.")


def add_application(user_id: int, nickname: str, platform: str):
    """Добавить новую заявку (с московским временем)"""
    created_at = datetime.now(MSK).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO applications (user_id, nickname, platform, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, nickname, platform, "pending", created_at)
        )
        db.commit()


def get_last_application(user_id: int):
    """Получить последнюю заявку пользователя"""
    with sqlite3.connect(DB_PATH) as db:
        cur = db.execute(
            "SELECT id, nickname, platform, status, created_at FROM applications WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,)
        )
        return cur.fetchone()


def update_application_status(user_id: int, status: str):
    """Обновить статус последней заявки"""
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "UPDATE applications SET status = ? WHERE user_id = ? AND status = 'pending'",
            (status, user_id)
        )
        db.commit()


def cancel_last_application(user_id: int):
    """Отменить последнюю заявку"""
    update_application_status(user_id, "canceled")


# --- ОБЯЗАТЕЛЬНО вызываем инициализацию базы при старте ---
init_db()

# -------------------- Глобальные фильтры уникальности --------------------

processed_events = set()

async def cleanup_event(unique_id: str):
    """Через 10 секунд событие можно будет снова обработать"""
    await asyncio.sleep(10)
    processed_events.discard(unique_id)

def is_event_processed(unique_id: str) -> bool:
    """Безопасный фильтр от повторной обработки событий"""
    if unique_id in processed_events:
        return True
    processed_events.add(unique_id)
    asyncio.create_task(cleanup_event(unique_id))  # безопасно и не ломает loop
    return False


# -------------------- ЛОГИ В КАНАЛ --------------------
async def send_log(guild: Optional[discord.Guild], message: str):
    """Отправка логов с московским временем"""
    if guild is None:
        print("⚠ Guild is None, cannot send log")
        return

    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        try:
            now_msk = datetime.now(MSK).strftime("%d.%m.%Y %H:%M:%S")
            await channel.send(f"[{now_msk}] 📝 {message}")
        except Exception as e:
            print(f"⚠ Не удалось отправить лог в канал: {e}")


# -------------------- VIEW ДЛЯ ЗАЯВОК --------------------
class ЗаявкаView(discord.ui.View):
    def __init__(self, author: discord.Member, ник: str, платформа: str, source_channel: discord.TextChannel):
        super().__init__(timeout=None)
        self.author = author
        self.ник = ник
        self.платформа = платформа.lower()
        self.source_channel = source_channel

    async def disable_buttons(self, interaction: discord.Interaction, label: str):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self, content=label)

    # ✅ Принять заявку
    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.green)
    async def принять(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("У тебя нет прав для этого!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        unique_id = f"accept-{interaction.message.id}"
        if is_event_processed(unique_id):
            await interaction.followup.send("❌ Эта заявка уже обработана.", ephemeral=True)
            return

        guild = interaction.guild
        main_role = discord.utils.get(guild.roles,
                                      name=ROLE_PLAYSTATION) if "playstation" in self.платформа else discord.utils.get(
            guild.roles, name=ROLE_PC)
        extra_role = None
        if self.платформа == "playstation4":
            extra_role = discord.utils.get(guild.roles, name=ROLE_PS4)
        elif self.платформа == "playstation5":
            extra_role = discord.utils.get(guild.roles, name=ROLE_PS5)

        initial_role = discord.utils.get(guild.roles, name=INITIAL_ROLE)
        remove_role = discord.utils.get(guild.roles, name=REMOVE_ROLE)

        roles_to_remove = [r for r in [initial_role, remove_role] if r in self.author.roles]
        if roles_to_remove:
            await self.author.remove_roles(*roles_to_remove)

        added_roles = []
        if main_role:
            await self.author.add_roles(main_role)
            added_roles.append(main_role.name)
        if extra_role:
            await self.author.add_roles(extra_role)
            added_roles.append(extra_role.name)

        try:
            await self.author.edit(nick=self.ник)
        except discord.Forbidden:
            await interaction.followup.send("❌ Не удалось сменить ник — у бота нет прав.", ephemeral=True)
            return

        update_application_status(self.author.id, "approved")
        processed_events.discard(f"anketa-{self.author.id}")

        await self.disable_buttons(interaction, "Заявка принята")
        await interaction.followup.send(f"✅ {self.author.display_name} получил роли: {', '.join(added_roles)}",
                                        ephemeral=True)
        await send_log(guild,
                       f"{interaction.user} принял заявку {self.author.display_name}")

    # ❌ Отклонить заявку
    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.red)
    async def отклонить(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("У тебя нет прав для этого!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        unique_id = f"decline-{interaction.message.id}"
        if is_event_processed(unique_id):
            await interaction.followup.send("❌ Эта заявка уже обработана.", ephemeral=True)
            return

        cancel_last_application(self.author.id)
        processed_events.discard(f"anketa-{self.author.id}")

        await self.disable_buttons(interaction, "Заявка отклонена")
        await interaction.followup.send(f"❌ Заявка {self.author.display_name} отклонена.", ephemeral=True)
        await send_log(interaction.guild,
                       f"{interaction.user} отклонил заявку {self.author.display_name}")

    # ✏️ Запросить изменения
    @discord.ui.button(label="✏️ Запросить изменения", style=discord.ButtonStyle.gray)
    async def запросить_изменения(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("У тебя нет прав для этого!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        unique_id = f"edit-{interaction.message.id}"
        if is_event_processed(unique_id):
            await interaction.followup.send("❌ Эта заявка уже обработана.", ephemeral=True)
            return

        cancel_last_application(self.author.id)
        processed_events.discard(f"anketa-{self.author.id}")

        await self.disable_buttons(interaction, "Изменения запрошены")
        if self.source_channel:
            await self.source_channel.send(
                f"✏️ {self.author.mention}, администратор {interaction.user.display_name} запросил изменения в вашей заявке. "
                "Пожалуйста, исправьте ник или выберите другую платформу и отправьте новую заявку."
            )
        await interaction.followup.send(f"✏️ Запрос на изменения отправлен {self.author.display_name}.", ephemeral=True)
        await send_log(interaction.guild,
                       f"{interaction.user} запросил изменения для заявки {self.author.display_name}")



# -------------------- СОБЫТИЯ --------------------
@bot.event
async def on_message_delete(message: discord.Message):
    unique_id = f"deleted-{message.id}"
    if is_event_processed(unique_id):
        return

    if message.guild is None:
        return
    try:
        channel = message.guild.get_channel(LOG_CHANNEL_ID)
        if not channel:
            return

        content = f"🛑 Сообщение удалено\nПользователь: {message.author.display_name}\nКанал: {message.channel.mention}\nСодержание: {message.content or '*(пустое сообщение)*'}"

        files = [await att.to_file() for att in message.attachments]

        await channel.send(content, files=files)
    except Exception as e:
        logger.error(f"Ошибка при логировании удалённого сообщения: {e}")




@bot.tree.command(name="whois", description="Посмотреть информацию о пользователе", guild=discord.Object(id=ALLOWED_GUILD_ID))
@app_commands.describe(user="Выберите пользователя")
async def whois(interaction: discord.Interaction, user: discord.Member):
    if interaction.channel_id != LOG_CHANNEL_ID:
        await interaction.response.send_message("❌ Эту команду можно использовать только в канале логов.", ephemeral=True)
        return

    embed = discord.Embed(title=f"Информация о {user.display_name}", color=discord.Color.blurple())
    embed.add_field(name="ID", value=user.id, inline=False)
    embed.add_field(name="Никнейм", value=user.display_name, inline=False)
    embed.add_field(name="Аккаунт создан", value=discord.utils.format_dt(user.created_at, "f"), inline=False)
    embed.add_field(name="Присоединился на сервер", value=discord.utils.format_dt(user.joined_at, "f"), inline=False)
    embed.add_field(name="Роли", value=", ".join([r.name for r in user.roles if r.name != "@everyone"]), inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)

    await interaction.response.send_message(embed=embed)  # <- больше не ephemeral



@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.content == after.content:
        return
    unique_id = f"edited-{before.id}"
    if is_event_processed(unique_id):
        return

    if before.guild is None:
        return
    try:
        channel = before.guild.get_channel(LOG_CHANNEL_ID)
        if not channel:
            return

        content = f"✏️ Сообщение изменено\nПользователь: {before.author.display_name}\nКанал: {before.channel.mention}\nСтарое: {before.content or '*(пустое сообщение)*'}\nНовое: {after.content or '*(пустое сообщение)*'}"

        files = [await att.to_file() for att in after.attachments]

        await channel.send(content, files=files)
    except Exception as e:
        logger.error(f"Ошибка при логировании изменённого сообщения: {e}")


# -------------------- /anketa --------------------
@bot.tree.command(
    name="anketa",
    description="Отправить заявку на роль",
    guild=discord.Object(id=ALLOWED_GUILD_ID)
)
@app_commands.describe(ник="Ваш ник", платформа="Ваша игровая платформа")
@app_commands.choices(платформа=[
    app_commands.Choice(name="PlayStation 4", value="playstation4"),
    app_commands.Choice(name="PlayStation 5", value="playstation5"),
    app_commands.Choice(name="PC", value="pc")
])
async def anketa(interaction: discord.Interaction, ник: str, платформа: app_commands.Choice[str]):
    # ✅ Деферим сразу, чтобы Discord не выбрасывал "Unknown interaction"
    await interaction.response.defer(ephemeral=True)

    unique_id = f"anketa-{interaction.user.id}"
    if is_event_processed(unique_id):
        await interaction.followup.send("❌ Ваша заявка уже обрабатывается.", ephemeral=True)
        return

    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.followup.send("Команда доступна только на этом сервере.", ephemeral=True)
        return

    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.followup.send("❌ Эту команду можно использовать только в чате новичков.", ephemeral=True)
        return

    last_app = get_last_application(interaction.user.id)
    if last_app and last_app[3] == "pending":
        await interaction.followup.send("❌ У вас уже есть активная заявка.", ephemeral=True)
        return

    add_application(interaction.user.id, ник, платформа.value)

    main_role = ROLE_PLAYSTATION if "playstation" in платформа.value else ROLE_PC
    extra_role = None
    if платформа.value == "playstation4":
        extra_role = ROLE_PS4
    elif платформа.value == "playstation5":
        extra_role = ROLE_PS5

    roles_to_assign = [main_role]
    if extra_role:
        roles_to_assign.append(extra_role)

    embed = discord.Embed(title="Новая заявка", color=discord.Color.blue())
    embed.add_field(name="Пользователь", value=interaction.user.mention, inline=False)
    embed.add_field(name="Ник", value=ник, inline=False)
    embed.add_field(name="Платформа", value=платформа.name, inline=False)
    embed.add_field(name="Роли, которые будут выданы", value=", ".join(roles_to_assign), inline=False)

    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if admin_channel is None:
        await interaction.followup.send("Ошибка: канал для заявок не найден.", ephemeral=True)
        return

    view = ЗаявкаView(
        author=interaction.user,
        ник=ник,
        платформа=платформа.value,
        source_channel=interaction.channel
    )
    await admin_channel.send(embed=embed, view=view)

    await send_log(
        interaction.guild,
        f"[{discord.utils.format_dt(discord.utils.utcnow(), 'f')}] "
        f"Новая заявка от {interaction.user.display_name} | Ник: {ник} | Платформа: {платформа.name}"
    )

    await interaction.followup.send("✅ Ваша заявка отправлена на рассмотрение.", ephemeral=True)





# -------------------- /my_application --------------------
@bot.tree.command(name="my_application", description="Статус вашей последней заявки",
                  guild=discord.Object(id=ALLOWED_GUILD_ID))
async def my_application(interaction: discord.Interaction):
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message("❌ Эту команду можно использовать только в чате новичков.", ephemeral=True)
        return

    app = get_last_application(interaction.user.id)
    if not app:
        await interaction.response.send_message("❌ У вас ещё нет заявок.", ephemeral=True)
        return
    app_id, nickname, platform, status, created_at = app
    embed = discord.Embed(title="Ваша заявка", color=discord.Color.green())
    embed.add_field(name="Ник", value=nickname, inline=False)
    embed.add_field(name="Платформа", value=platform, inline=False)
    embed.add_field(name="Статус", value=status, inline=False)
    embed.add_field(name="Создана", value=discord.utils.format_dt(discord.utils.utcnow(), 'f'), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# -------------------- /cancel_application --------------------
@bot.tree.command(name="cancel_application", description="Отменить свою заявку",
                  guild=discord.Object(id=ALLOWED_GUILD_ID))
async def cancel_application(interaction: discord.Interaction):
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message("❌ Эту команду можно использовать только в чате новичков.", ephemeral=True)
        return

    app = get_last_application(interaction.user.id)
    if not app or app[3] != "pending":
        await interaction.response.send_message("❌ У вас нет активной заявки для отмены.", ephemeral=True)
        return

    cancel_last_application(interaction.user.id)
    processed_events.discard(f"anketa-{interaction.user.id}")

    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if admin_channel:
        async for message in admin_channel.history(limit=100):
            if message.embeds:
                embed = message.embeds[0]
                if embed.fields and embed.fields[0].value == interaction.user.mention:
                    await message.edit(content="🚫 Заявка отменена пользователем.", view=None)
                    break

    await interaction.response.send_message("🚫 Ваша заявка отменена.", ephemeral=True)
    await send_log(interaction.guild,
                   f"[{discord.utils.format_dt(discord.utils.utcnow(), 'f')}] {interaction.user.display_name} отменил свою заявку")



@bot.tree.command(
    name="purge",
    description="Удалить последние сообщения в этом канале",
    guild=discord.Object(id=ALLOWED_GUILD_ID)
)
@app_commands.describe(
    amount="Сколько сообщений удалить (по умолчанию 10, максимум 100)",
    user="Удалить только сообщения этого пользователя (опционально)"
)
async def purge(interaction: discord.Interaction, amount: int = 10, user: Optional[discord.Member] = None):
    try:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
            return

        if amount <= 0 or amount > 100:
            await interaction.response.send_message("⚠ Количество должно быть от 1 до 100.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)

        def check(msg: discord.Message):
            if msg.created_at <= two_weeks_ago:
                return False
            if user and msg.author != user:
                return False
            return True

        try:
            deleted = await interaction.channel.purge(limit=amount, check=check)
        except discord.HTTPException as e:
            await interaction.followup.send(f"⚠ Ошибка при удалении: {e}", ephemeral=True)
            return

        summary = f"🧹 Удалено {len(deleted)} сообщений{' от ' + user.display_name if user else ''}."
        await interaction.followup.send(summary, ephemeral=True)

        # Логируем только если база данных не занята
        try:
            await send_log(interaction.guild, f"{interaction.user.display_name} очистил {len(deleted)} сообщений.")
        except Exception as log_err:
            print(f"[purge] Ошибка логирования: {log_err}")

    except Exception as e:
        print(f"[purge] Ошибка: {e}")



@bot.tree.command(
    name="avatar",
    description="Показать аватар пользователя",
    guild=discord.Object(id=ALLOWED_GUILD_ID)
)
@app_commands.describe(user="Выберите пользователя (по умолчанию — вы)")
async def avatar(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    if user is None:
        user = interaction.user  # если пользователь не указал ник, показываем свой аватар

    embed = discord.Embed(title=f"Аватар {user.display_name}", color=discord.Color.blurple())
    embed.set_image(url=user.display_avatar.url)
    embed.set_footer(text=f"ID: {user.id}")

    await interaction.response.send_message(embed=embed)


from discord.ui import View, Button

class SimpleHelpView(View):
    def __init__(self, pages):
        super().__init__(timeout=None)
        self.pages = pages
        self.current = 0

        # кнопки
        self.info_btn = Button(label="ℹ️ О боте", style=discord.ButtonStyle.secondary)
        self.user_btn = Button(label="Пользователь 🟢", style=discord.ButtonStyle.green)
        self.admin_btn = Button(label="Админ 🟡", style=discord.ButtonStyle.red)
        self.roles_btn = Button(label="Роли 🔵", style=discord.ButtonStyle.blurple)

        self.info_btn.callback = self.show_info
        self.user_btn.callback = self.show_user
        self.admin_btn.callback = self.show_admin
        self.roles_btn.callback = self.show_roles

        self.add_item(self.info_btn)
        self.add_item(self.user_btn)
        self.add_item(self.admin_btn)
        self.add_item(self.roles_btn)

        self.update_buttons()

    async def show_info(self, interaction: discord.Interaction):
        self.current = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def show_user(self, interaction: discord.Interaction):
        self.current = 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def show_admin(self, interaction: discord.Interaction):
        self.current = 2
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def show_roles(self, interaction: discord.Interaction):
        self.current = 3
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    def update_buttons(self):
        self.info_btn.label = "ℹ️ О боте ✅" if self.current == 0 else "ℹ️ О боте"
        self.user_btn.label = "Пользователь ✅" if self.current == 1 else "Пользователь 🟢"
        self.admin_btn.label = "Админ ✅" if self.current == 2 else "Админ 🟡"
        self.roles_btn.label = "Роли ✅" if self.current == 3 else "Роли 🔵"


# ---------------- Создание страниц ----------------
def create_help_pages():
    info_embed = discord.Embed(
        title="ℹ️ О боте",
        description=(
            "Этот бот помогает управлять сервером и заявками игроков.\n\n"
            "**Основные функции:**\n"
            "🔹 Сохраняет **удалённые** и **изменённые** сообщения (чтобы ничего не потерялось).\n"
            "🔹 Позволяет игрокам отправлять **заявки на игровые роли** и менять платформу и ник.\n"
            "🔹 Упрощает работу администраторов с ролями и управлением.\n"
            "🔹 Имеет удобный `/help` с категориями команд.\n"
            "🔹 Защита от мошшеничества.\n"
            "🔹 Напоминания пользователям.\n"
        ),
        color=discord.Color.blue()
    )
    info_embed.set_footer(text="Категория: О боте")

    user_embed = discord.Embed(title="📘 Команды для пользователей", color=discord.Color.green())
    user_embed.add_field(name="/avatar [user]", value="Показать аватар выбранного пользователя.", inline=False)
    user_embed.add_field(name="/stats", value="Показать общую статистику сообщений.", inline=False)
    user_embed.add_field(name="/remind", value="Создает напоминание.", inline=False)
    user_embed.add_field(name="/top10_month", value="ТОП-10 за месяц.", inline=False)
    user_embed.add_field(name="/top10_week", value="ТОП-10 за неделю.", inline=False)
    user_embed.add_field(name="/help", value="О боте.", inline=False)
    user_embed.set_footer(text="Категория: Пользователь")

    admin_embed = discord.Embed(title="🛠 Команды для администраторов", color=discord.Color.red())
    admin_embed.add_field(name="/whois [user]", value="Посмотреть информацию о пользователе.", inline=False)
    admin_embed.add_field(name="/purge [amount] [user]", value="Удалить последние сообщения в канале.", inline=False)
    admin_embed.add_field(name="/all_applications", value="Показать историю всех заявок.", inline=False)
    admin_embed.add_field(name="/isolator", value="Отправить нарушителя в изолятор.", inline=False)
    admin_embed.add_field(name="/unisolator", value="Вытащить нарушителя из изолятора.", inline=False)
    admin_embed.set_footer(text="Категория: Админ")

    roles_embed = discord.Embed(title="🎮 Команды для работы с ролями", color=discord.Color.blurple())
    roles_embed.add_field(name="/anketa", value="Отправить заявку на игровую роль. Нужно указать ник и платформу.", inline=False)
    roles_embed.add_field(name="/my_application", value="Проверить статус вашей последней заявки.", inline=False)
    roles_embed.add_field(name="/cancel_application", value="Отменить активную заявку.", inline=False)
    roles_embed.add_field(name="/change_platform", value="Смена платформы с возможностью смены ника.", inline=False)
    roles_embed.set_footer(text="Категория: Роли")

    return [info_embed, user_embed, admin_embed, roles_embed]


# ---------------- Команда /help ----------------
@bot.tree.command(
    name="help",
    description="Интерактивный справочник команд",
    guild=discord.Object(id=ALLOWED_GUILD_ID)
)
async def help_command(interaction: discord.Interaction):
    pages = create_help_pages()
    view = SimpleHelpView(pages)

    if not interaction.response.is_done():
        await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)
    else:
        await interaction.followup.send(embed=pages[0], view=view, ephemeral=True)





# Названия ролей (будем искать по имени)
ROLE_PLAYSTATION = "AGPG 🚘"
ROLE_PC = "Гость 🎩"
ROLE_PS4 = "PS4 player"
ROLE_PS5 = "PS5 player"

COMMANDS_CHANNEL_ID = int(os.getenv("COMMANDS_CHANNEL_ID"))  # ID канала команд


# --- Смена платформы ---
@bot.tree.command(
    name="change_platform",
    description="Сменить игровую платформу (PS4, PS5, PC)"
)
@app_commands.describe(
    platform="Выбери новую платформу",
    nickname="Необязательная смена ника"
)
@app_commands.choices(platform=[
    app_commands.Choice(name="PS4", value="ps4"),
    app_commands.Choice(name="PS5", value="ps5"),
    app_commands.Choice(name="PC (Гость)", value="pc")
])
async def change_platform(
    interaction: discord.Interaction,
    platform: app_commands.Choice[str],
    nickname: Optional[str] = None
):
    # Ограничиваем выполнение командным каналом
    if interaction.channel.id != COMMANDS_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ Эту команду можно использовать только в канале команд!",
            ephemeral=True
        )
        return

    guild = interaction.guild
    member = interaction.user

    # Получаем роли по имени
    role_ps4 = discord.utils.get(guild.roles, name=ROLE_PS4)
    role_ps5 = discord.utils.get(guild.roles, name=ROLE_PS5)
    role_pc = discord.utils.get(guild.roles, name=ROLE_PC)
    role_playstation = discord.utils.get(guild.roles, name=ROLE_PLAYSTATION)

    if not all([role_ps4, role_ps5, role_pc, role_playstation]):
        await interaction.response.send_message(
            "⚠️ Не все игровые роли найдены на сервере. Обратись к администратору.",
            ephemeral=True
        )
        return

    # Убираем старые роли
    await member.remove_roles(role_ps4, role_ps5, role_pc, role_playstation)

    # Выдаём новые
    if platform.value == "ps4":
        await member.add_roles(role_ps4, role_playstation)
        msg = "🎮 Твоя платформа изменена на **PS4**"
    elif platform.value == "ps5":
        await member.add_roles(role_ps5, role_playstation)
        msg = "🎮 Твоя платформа изменена на **PS5**"
    elif platform.value == "pc":
        await member.add_roles(role_pc)
        msg = "💻 Твоя платформа изменена на **PC (Гость)**"
    else:
        msg = "❌ Ошибка при выборе платформы."

    # Если указал ник – меняем
    if nickname:
        try:
            await member.edit(nick=nickname)
            msg += f"\n✏️ Ник изменён на **{nickname}**"
        except discord.Forbidden:
            msg += "\n⚠️ Не удалось изменить ник (нет прав)."

    await interaction.response.send_message(msg, ephemeral=True)



from collections import defaultdict, deque
from datetime import datetime, timedelta

# Хранилища
user_messages = defaultdict(deque)        # user_id -> список времени сообщений для антиспама
all_time_stats = defaultdict(int)         # общая статистика
weekly_stats = defaultdict(int)           # статистика за неделю
monthly_stats = defaultdict(int)          # статистика за месяц
reminders = []                             # список активных напоминаний

BAD_WORDS = [ "free nitro", "дискорд.гг"]  # стоп-слова

last_week_reset = datetime.now()
last_month_reset = datetime.now()

# -------------------- АНТИСПАМ + ФИЛЬТРЫ --------------------
from collections import defaultdict, deque
import re
from discord import app_commands
import discord

# -------------------- ХРАНИЛИЩА --------------------
user_messages = defaultdict(deque)        # user_id -> список времени сообщений для антиспама
all_time_stats = defaultdict(int)         # общая статистика
weekly_stats = defaultdict(int)           # статистика за неделю
monthly_stats = defaultdict(int)          # статистика за месяц
reminders = []                             # список активных напоминаний

BAD_WORDS = [ "free nitro", "дискорд.гг"]  # стоп-слова

# -------------------- ДАМИР-ЗАЩИТА --------------------
# Чтобы бот отвечал на "дамир" не чаще одного раза в 5 минут на сервер
last_damir_reply = {}  # guild_id -> время последнего ответа

# -------------------- on_message --------------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    now = datetime.now()

    # -------------------- АНТИСПАМ --------------------
    user_messages[message.author.id].append(now)
    while user_messages[message.author.id] and (now - user_messages[message.author.id][0]).seconds > 10:
        user_messages[message.author.id].popleft()
    if len(user_messages[message.author.id]) > 5:
        mute_role = discord.utils.get(message.guild.roles, name="Muted")
        if mute_role:
            await message.author.add_roles(mute_role)
            await message.channel.send(f"🚫 {message.author.mention} замьючен за спам!")

    # -------------------- ФИЛЬТР ЗАПРЕЩЁННЫХ СЛОВ --------------------
    for bad in BAD_WORDS:
        if re.search(bad, message.content.lower()):
            await message.delete()
            await message.channel.send(f"⚠️ {message.author.mention}, запрещённое слово!", delete_after=5)
            return

    # -------------------- СЛОВО "ДАМИР" С ЗАЩИТОЙ 5 МИНУТ ПО КАНАЛУ --------------------
    cooldown_seconds = 300  # 5 минут
    channel_id = message.channel.id
    last_time = last_damir_reply.get(channel_id)

    if "дамир" in message.content.lower():
        if not last_time or (now - last_time).total_seconds() > cooldown_seconds:
            await message.channel.send("Дамир — легенда пх")
            last_damir_reply[channel_id] = now
        else:
            # сообщение "попробуйте позже" один раз за кулдаун
            if last_damir_reply.get(f"{channel_id}_cooldown_msg") is None:
                await message.channel.send(
                    "Хохо, легендой пх он может быть только раз в 5 минут. Попробуй позже."
                )
                last_damir_reply[f"{channel_id}_cooldown_msg"] = now

    # -------------------- СБРОС КУЛДАУНА ДЛЯ 'ПОПРОБУЙТЕ ПОЗЖЕ' --------------------
    cooldown_msg_time = last_damir_reply.get(f"{channel_id}_cooldown_msg")
    if cooldown_msg_time and (now - cooldown_msg_time).total_seconds() > cooldown_seconds:
        del last_damir_reply[f"{channel_id}_cooldown_msg"]

    # -------------------- СТАТИСТИКА --------------------
    all_time_stats[message.author.id] += 1
    weekly_stats[message.author.id] += 1
    monthly_stats[message.author.id] += 1

    # -------------------- ПРОХОД КОМАНД --------------------
    await bot.process_commands(message)



# -------------------- ПРОВЕРКА ПОДОЗРИТЕЛЬНЫХ НИКОВ --------------------
@bot.event
async def on_member_join(member: discord.Member):
    suspicious_patterns = [r"free\s*n[i1]tro", r"discord\.gg", r"http", r"\.ru", r"\.com"]
    for pattern in suspicious_patterns:
        if re.search(pattern, member.display_name.lower()):
            log_channel = member.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"🚨 Подозрительный ник: {member.mention} ({member.display_name})")
            break



# -------------------- НАПОМИНАНИЯ /remind --------------------
@bot.tree.command(name="remind", description="Создать напоминание")
@app_commands.describe(time="Через сколько (например: 10m, 2h, 1d)", text="Текст напоминания")
async def remind(interaction: discord.Interaction, time: str, text: str):
    delay = 0
    if time.endswith("m"):
        delay = int(time[:-1]) * 60
    elif time.endswith("h"):
        delay = int(time[:-1]) * 3600
    elif time.endswith("d"):
        delay = int(time[:-1]) * 86400
    else:
        await interaction.response.send_message("❌ Укажи время в формате: 10m, 2h, 1d", ephemeral=True)
        return

    remind_time = datetime.now() + timedelta(seconds=delay)
    reminders.append((interaction.user.id, remind_time, text))

    await interaction.response.send_message(f"✅ Напоминание установлено через {time}: **{text}**", ephemeral=True)

    async def reminder_task():
        await asyncio.sleep(delay)
        user = interaction.guild.get_member(interaction.user.id)
        if user:
            try:
                await user.send(f"⏰ Напоминание: {text}")
            except:
                pass

    asyncio.create_task(reminder_task())


# -------------------- СТАТИСТИКА --------------------
@bot.tree.command(name="stats", description="Показать общую статистику сообщений")
async def stats_command(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except discord.InteractionResponded:
        pass

    guild = interaction.guild
    lines = []
    for member_id, count in all_time_stats.items():
        member = guild.get_member(member_id)
        if member:
            lines.append(f"**{member.display_name}** — {count} сообщений")

    if not lines:
        await interaction.followup.send("Пока нет статистики.")
        return

    embed = discord.Embed(title="📊 Общая статистика сообщений", color=discord.Color.gold())
    embed.description = "\n".join(lines[:20])
    await interaction.followup.send(embed=embed)


# -------------------- ТОП-10 за неделю --------------------
@bot.tree.command(name="top10_week", description="ТОП-10 за неделю")
async def top10_week(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except discord.InteractionResponded:
        pass

    guild = interaction.guild
    sorted_stats = sorted(weekly_stats.items(), key=lambda x: x[1], reverse=True)[:10]

    if not sorted_stats:
        await interaction.followup.send("Нет данных за неделю.")
        return

    embed = discord.Embed(title="🏆 ТОП-10 за неделю", color=discord.Color.blue())
    for idx, (member_id, count) in enumerate(sorted_stats, start=1):
        member = guild.get_member(member_id)
        if member:
            embed.add_field(name=f"{idx}. {member.display_name}", value=f"{count} сообщений", inline=False)
    await interaction.followup.send(embed=embed)


# -------------------- ТОП-10 за месяц --------------------
@bot.tree.command(name="top10_month", description="ТОП-10 за месяц")
async def top10_month(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except discord.InteractionResponded:
        pass

    guild = interaction.guild
    sorted_stats = sorted(monthly_stats.items(), key=lambda x: x[1], reverse=True)[:10]

    if not sorted_stats:
        await interaction.followup.send("Нет данных за месяц.")
        return

    embed = discord.Embed(title="🏆 ТОП-10 за месяц", color=discord.Color.purple())
    for idx, (member_id, count) in enumerate(sorted_stats, start=1):
        member = guild.get_member(member_id)
        if member:
            embed.add_field(name=f"{idx}. {member.display_name}", value=f"{count} сообщений", inline=False)
    await interaction.followup.send(embed=embed)



# -------------------- ФОНОВАЯ ЗАДАЧА ДЛЯ СБРОСА СТАТИСТИКИ --------------------
async def reset_stats_task():
    global last_week_reset, last_month_reset
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()
        log_channel = None
        for guild in bot.guilds:
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                break

        # сброс еженедельной статистики
        if (now - last_week_reset).days >= 7:
            weekly_stats.clear()
            last_week_reset = now
            if log_channel:
                await log_channel.send("📆 Статистика **за неделю** обнулена!")

        # сброс ежемесячной статистики
        if (now - last_month_reset).days >= 30:
            monthly_stats.clear()
            last_month_reset = now
            if log_channel:
                await log_channel.send("🗓 Статистика **за месяц** обнулена!")

        await asyncio.sleep(3600)  # проверка каждый час





from discord.ui import View, Button

class ApplicationsView(View):
    def __init__(self, rows, guild: discord.Guild, page_size=5):
        super().__init__(timeout=None)
        self.rows = rows
        self.guild = guild
        self.page_size = page_size
        self.current_page = 0
        self.total_pages = (len(rows) + page_size - 1) // page_size

        # Кнопки навигации
        self.prev_btn = Button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
        self.next_btn = Button(label="➡️ Вперед", style=discord.ButtonStyle.secondary)
        self.prev_btn.callback = self.prev_page
        self.next_btn.callback = self.next_page
        self.add_item(self.prev_btn)
        self.add_item(self.next_btn)
        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = self.current_page == 0
        self.next_btn.disabled = self.current_page >= self.total_pages - 1

    async def prev_page(self, interaction: discord.Interaction):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def next_page(self, interaction: discord.Interaction):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def get_embed(self):
        start = self.current_page * self.page_size
        end = start + self.page_size
        embed = discord.Embed(title=f"📄 Заявки (Страница {self.current_page+1}/{self.total_pages})",
                              color=discord.Color.orange())
        for user_id, nickname, platform, status, created_at in self.rows[start:end]:
            member = self.guild.get_member(user_id)
            mention = member.mention if member else f"ID:{user_id}"
            display_name = member.display_name if member else nickname
            embed.add_field(
                name=f"{display_name} | {status.capitalize()}",
                value=f"Пользователь: {mention}\nНик: {nickname}\nПлатформа: {platform}\nДата: {created_at}",
                inline=False
            )
        return embed

class ApplicationsView(discord.ui.View):
    def __init__(self, rows, guild: discord.Guild):
        super().__init__(timeout=180)
        self.rows = rows
        self.guild = guild
        self.page = 0
        self.per_page = 5

    def get_embed(self):
        embed = discord.Embed(
            title="📋 Все заявки",
            color=discord.Color.blue()
        )

        start = self.page * self.per_page
        end = start + self.per_page
        page_rows = self.rows[start:end]

        for user_id, nickname, platform, status, created_at in page_rows:
            user = self.guild.get_member(user_id)
            name = user.mention if user else f"<@{user_id}>"

            embed.add_field(
                name=name,
                value=(
                    f"**Ник:** `{nickname}`\n"
                    f"**Платформа:** `{platform}`\n"
                    f"**Статус:** `{status}`\n"
                    f"**Дата:** {created_at}"
                ),
                inline=False
            )

        embed.set_footer(
            text=f"Страница {self.page + 1} / {(len(self.rows) - 1) // self.per_page + 1}"
        )
        return embed

    # ⬅️ Назад
    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()

    # ➡️ Вперёд
    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def forward(self, interaction: discord.Interaction, button: discord.ui.Button):
        max_page = (len(self.rows) - 1) // self.per_page
        if self.page < max_page:
            self.page += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()

    # 🗑️ Удалить все заявки
    @discord.ui.button(label="🗑️ Удалить все заявки", style=discord.ButtonStyle.danger)
    async def delete_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ У тебя нет прав для удаления заявок.",
                ephemeral=True
            )
            return

        with sqlite3.connect(DB_PATH) as db:
            db.execute("DELETE FROM applications")
            db.commit()

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="✅ **Все заявки успешно удалены.**",
            embed=None,
            view=self
        )

QUESTION_LOG_CHANNEL_ID = int(os.getenv("QUESTION_LOG_CHANNEL_ID"))

# -------------------- DM LISTENER --------------------
@bot.listen("on_message")
async def dm_logger(message: discord.Message):
    if message.author.bot:
        return

    # Только ЛС
    if message.guild is None:
        try:
            channel = await bot.fetch_channel(QUESTION_LOG_CHANNEL_ID)

            embed = discord.Embed(
                title=f"📩 DM от {message.author}",
                description=message.content or "*Без текста*",
                color=discord.Color.blurple()
            )
            embed.add_field(
                name="👤 Пользователь",
                value=f"{message.author} (`{message.author.id}`)",
                inline=False
            )

            # Подготовка файлов
            files_to_send = []
            for att in message.attachments:
                # Скачиваем файл и прикрепляем
                file = await att.to_file()
                files_to_send.append(file)

            # Отправка
            await channel.send(embed=embed, files=files_to_send)
            print("✅ SENT TO LOG CHANNEL")

        except Exception as e:
            print("❌ DM LOGGER ERROR:", repr(e))



@bot.tree.command(
    name="all_applications",
    description="Показать историю всех заявок (только для админов)",
    guild=discord.Object(id=ALLOWED_GUILD_ID)
)
@app_commands.describe(
    status="Фильтр по статусу заявки (pending, approved, canceled)"
)
async def all_applications(
    interaction: discord.Interaction,
    status: Optional[str] = None
):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ У тебя нет прав для просмотра всех заявок.",
            ephemeral=True
        )
        return

    query = "SELECT user_id, nickname, platform, status, created_at FROM applications"
    params = ()

    if status:
        query += " WHERE status = ?"
        params = (status.lower(),)

    query += " ORDER BY created_at DESC"

    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute(query, params).fetchall()

    if not rows:
        await interaction.response.send_message(
            "❌ Заявки не найдены.",
            ephemeral=True
        )
        return

    view = ApplicationsView(rows, interaction.guild)
    await interaction.response.send_message(
        embed=view.get_embed(),
        view=view,
        ephemeral=True
    )



from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging
import discord

# Хранилище действий админов: admin_id -> [(time, action)]
admin_actions = defaultdict(deque)

# Настройки
BAN_THRESHOLD = 3
KICK_THRESHOLD = 3
WINDOW_MINUTES = 60
DELETE_CHANNEL_THRESHOLD = 2
DELETE_ROLE_THRESHOLD = 2

# Интервал задержек между банами (чтобы не ловить rate limit)
BAN_DELAY = 2  # секунды

async def safe_ban(guild: discord.Guild, member: discord.Member, reason: str, log_channel=None):
    """Безопасный бан с обработкой ошибок и задержкой"""
    try:
        if not member:
            return
        if not guild.me.guild_permissions.ban_members:
            raise PermissionError("У бота нет прав на бан участников.")
        if guild.me.top_role <= member.top_role:
            raise PermissionError("Роль бота ниже роли участника.")

        await guild.ban(member, reason=reason, delete_message_days=0)
        if log_channel:
            await log_channel.send(f"🚨 **AGPG Guard:** {member.mention} забанен. Причина: {reason}")
        logging.warning(f"AGPG Guard: {member} забанен. Причина: {reason}")

        # небольшая задержка, чтобы избежать rate limit
        await asyncio.sleep(BAN_DELAY)

    except discord.HTTPException as e:
        logging.error(f"Ошибка Discord при бане {member}: {e}")
        if log_channel:
            await log_channel.send(f"⚠️ Ошибка при бане {member}: {e}")
    except Exception as e:
        logging.error(f"Не удалось забанить {member}: {e}")
        if log_channel:
            await log_channel.send(f"⚠️ Не удалось забанить {member}: {e}")


async def check_admin_abuse(guild: discord.Guild, admin: discord.Member):
    """Проверка на превышение лимитов банов/киков"""
    now = datetime.utcnow()
    logs = admin_actions[admin.id]

    while logs and (now - logs[0][0]).total_seconds() > WINDOW_MINUTES * 60:
        logs.popleft()

    bans = sum(1 for t, a in logs if a == "ban")
    kicks = sum(1 for t, a in logs if a == "kick")

    if bans >= BAN_THRESHOLD or kicks >= KICK_THRESHOLD:
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        reason = f"AGPG Guard: превысил лимит банов/киков ({bans} банов, {kicks} киков)."
        await safe_ban(guild, admin, reason, log_channel)


@bot.event
async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
    """Основная защита от злоупотреблений"""
    try:
        guild = entry.guild
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        admin = entry.user
        target = entry.target

        if not isinstance(admin, (discord.Member, discord.User)):
            return
        if admin.bot or admin.id == guild.owner_id:
            return

        now = datetime.utcnow()

        # --------------- Бан / Кик ---------------
        if entry.action in (discord.AuditLogAction.ban, discord.AuditLogAction.kick):
            action = "ban" if entry.action == discord.AuditLogAction.ban else "kick"
            if isinstance(target, (discord.Member, discord.User)) and getattr(target, "bot", False):
                return

            admin_actions[admin.id].append((now, action))
            logging.info(f"[AGPG GUARD] {admin} сделал {action} → {target}")
            await check_admin_abuse(guild, admin)

        # --------------- Добавление бота ---------------
        elif entry.action == discord.AuditLogAction.bot_add:
            if not isinstance(target, (discord.Member, discord.User)) or not getattr(target, "bot", False):
                return
            logging.warning(f"[AGPG GUARD] {admin} добавил бота {target} — бан!")

            member = guild.get_member(admin.id)
            await safe_ban(guild, member, f"AGPG Guard: добавил бота {target}.", log_channel)
            await safe_ban(guild, target, "AGPG Guard: автоматически заблокирован после добавления.", log_channel)

        # --------------- Удаление каналов ---------------
        elif entry.action == discord.AuditLogAction.channel_delete:
            admin_actions[admin.id].append((now, "del_channel"))
            recent = [a for t, a in admin_actions[admin.id] if a == "del_channel" and (now - t).total_seconds() <= WINDOW_MINUTES * 60]

            if len(recent) >= DELETE_CHANNEL_THRESHOLD:
                member = guild.get_member(admin.id)
                await safe_ban(guild, member, f"AGPG Guard: удалил {len(recent)} каналов за короткое время.", log_channel)

        # --------------- Удаление ролей ---------------
        elif entry.action == discord.AuditLogAction.role_delete:
            admin_actions[admin.id].append((now, "del_role"))
            recent = [a for t, a in admin_actions[admin.id] if a == "del_role" and (now - t).total_seconds() <= WINDOW_MINUTES * 60]

            if len(recent) >= DELETE_ROLE_THRESHOLD:
                member = guild.get_member(admin.id)
                await safe_ban(guild, member, f"AGPG Guard: удалил {len(recent)} ролей за короткое время.", log_channel)

    except Exception as e:
        logging.error(f"Ошибка в on_audit_log_entry_create: {e}")
        try:
            guild = entry.guild
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"⚠️ Ошибка AGPG Guard: {e}")
        except:
            pass


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    """Глобальная защита от ошибок Discord interaction"""
    try:
        # Игнорируем известные неопасные ошибки
        if isinstance(error, discord.errors.NotFound) and "Unknown interaction" in str(error):
            return
        if isinstance(error, discord.errors.InteractionResponded):
            return

        # Отправляем аккуратное сообщение об ошибке
        if interaction.response.is_done():
            await interaction.followup.send(
                f"⚠️ Ошибка при выполнении команды: {error}", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Ошибка при выполнении команды: {error}", ephemeral=True
            )

    except Exception as e:
        # На случай, если даже отправка ответа упадет
        print(f"[AGPG ERROR] Ошибка при обработке исключения: {e}")




import sqlite3
import os
import time
import discord
from discord import app_commands

# -------------------- DATABASE --------------------

db = sqlite3.connect("isolator.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS isolator (
    user_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    roles TEXT,
    end_time INTEGER
)
""")
db.commit()

# -------------------- ENV --------------------

ISOLATOR_ROLE_ID = int(os.getenv("ISOLATOR_ROLE_ID"))
BOOSTER_ROLE_NAME = os.getenv("BOOSTER_ROLE_NAME")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

# -------------------- /isolator --------------------

@bot.tree.command(
    name="isolator",
    description="Выдать изолятор пользователю (в днях)",
    guild=discord.Object(id=ALLOWED_GUILD_ID)
)
@app_commands.describe(
    user="Пользователь",
    days="На сколько дней"
)
async def isolator(
    interaction: discord.Interaction,
    user: discord.Member,
    days: int
):
    await interaction.response.defer(ephemeral=True)

    if not (
        interaction.user.guild_permissions.administrator
        or interaction.user.guild_permissions.manage_roles
    ):
        await interaction.followup.send("❌ Нет прав.")
        return

    if days <= 0:
        await interaction.followup.send("❌ Количество дней должно быть больше 0.")
        return

    guild = interaction.guild
    isolator_role = guild.get_role(ISOLATOR_ROLE_ID)
    log_channel = guild.get_channel(LOG_CHANNEL_ID)

    if any(r.name == BOOSTER_ROLE_NAME for r in user.roles):
        await interaction.followup.send("🚫 Бустерам нельзя выдать изолятор.")
        return

    cursor.execute(
        "SELECT 1 FROM isolator WHERE user_id = ?",
        (user.id,)
    )
    if cursor.fetchone():
        await interaction.followup.send("⚠️ Пользователь уже в изоляторе.")
        return

    saved_roles = [r.id for r in user.roles if r != guild.default_role]

    await user.remove_roles(
        *[guild.get_role(r) for r in saved_roles if guild.get_role(r)],
        reason="Изолятор"
    )
    await user.add_roles(isolator_role, reason="Изолятор")

    end_time = int(time.time()) + days * 86400

    cursor.execute(
        "INSERT INTO isolator VALUES (?, ?, ?, ?)",
        (
            user.id,
            guild.id,
            ",".join(map(str, saved_roles)),
            end_time
        )
    )
    db.commit()

    await interaction.followup.send(
        f"🔒 {user.mention} изолирован на **{days} дн.**"
    )

    if log_channel:
        await log_channel.send(
            f"🔒 **Изолятор**\n"
            f"👤 Пользователь: {user}\n"
            f"📅 Срок: {days} дн.\n"
            f"👮 Модератор: {interaction.user}"
        )

# -------------------- /unisolator --------------------

@bot.tree.command(
    name="unisolator",
    description="Досрочно снять изолятор",
    guild=discord.Object(id=ALLOWED_GUILD_ID)
)
@app_commands.describe(user="Пользователь")
async def unisolator(
    interaction: discord.Interaction,
    user: discord.Member
):
    await interaction.response.defer(ephemeral=True)

    if not (
        interaction.user.guild_permissions.administrator
        or interaction.user.guild_permissions.manage_roles
    ):
        await interaction.followup.send("❌ Нет прав.")
        return

    cursor.execute(
        "SELECT roles FROM isolator WHERE user_id = ?",
        (user.id,)
    )
    row = cursor.fetchone()
    if not row:
        await interaction.followup.send("❌ Пользователь не в изоляторе.")
        return

    roles = [
        interaction.guild.get_role(int(r))
        for r in row[0].split(",")
        if interaction.guild.get_role(int(r))
    ]

    await user.remove_roles(
        interaction.guild.get_role(ISOLATOR_ROLE_ID),
        reason="Снятие изолятора"
    )
    await user.add_roles(*roles)

    cursor.execute(
        "DELETE FROM isolator WHERE user_id = ?",
        (user.id,)
    )
    db.commit()

    await interaction.followup.send(
        f"🔓 {user.mention} освобождён."
    )

# -------------------- RESTORE AFTER RESTART --------------------

@bot.event
async def on_ready():
    print("Bot ready")

    cursor.execute("SELECT * FROM isolator")
    rows = cursor.fetchall()

    for user_id, guild_id, roles, end_time in rows:
        guild = bot.get_guild(guild_id)
        if not guild:
            continue

        member = guild.get_member(user_id)
        if not member:
            continue

        remaining = end_time - int(time.time())
        if remaining <= 0:
            await remove_isolator(member, roles)
        else:
            asyncio.create_task(wait_and_release(member, roles, remaining))

async def wait_and_release(member, roles, seconds):
    await asyncio.sleep(seconds)
    await remove_isolator(member, roles)

async def remove_isolator(member, roles):
    guild = member.guild
    isolator_role = guild.get_role(ISOLATOR_ROLE_ID)

    role_objs = [
        guild.get_role(int(r))
        for r in roles.split(",")
        if guild.get_role(int(r))
    ]

    await member.remove_roles(isolator_role, reason="Окончание изолятора")
    await member.add_roles(*role_objs)

    cursor.execute(
        "DELETE FROM isolator WHERE user_id = ?",
        (member.id,)
    )
    db.commit()




@bot.event
async def on_ready():
    # Устанавливаем статус "Играет в Grand Theft Auto"
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="Grand Theft Auto V")
    )

    # Синхронизируем команды
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=ALLOWED_GUILD_ID))
        print(f"✅ Успешно синхронизировано {len(synced)} команд.")
    except Exception as e:
        print(f"⚠️ Ошибка при синхронизации команд: {e}")

    print(f"🤖 Бот {bot.user} запущен и готов к работе!")




import discord
from discord import app_commands


# -------------------- КОМАНДА ДЛЯ ОВНЕРА --------------------
@bot.tree.command(
    name="announce_meeting",
    description="Отправить личное сообщение участникам роли (только для овнера сервера)"
)
@app_commands.describe(
    role="Выберите роль, которой будет отправлено сообщение",
    meeting_type="Тип объявления",
    custom_text="Текст сообщения, которое будет отправлено в ЛС"
)
@app_commands.choices(meeting_type=[
    app_commands.Choice(name="Сходка PC 🚘", value="PC"),
    app_commands.Choice(name="Сходка PS5 🚘", value="PS5"),
    app_commands.Choice(name="Сходка PS4 🚘", value="PS4"),
    app_commands.Choice(name="Новость 📰", value="NEWS"),
])
async def announce_meeting(
    interaction: discord.Interaction,
    role: discord.Role,
    meeting_type: app_commands.Choice[str],
    custom_text: str
):
    # Только владелец сервера может использовать
    if interaction.user != interaction.guild.owner:
        await interaction.response.send_message(
            "❌ Только владелец сервера может использовать эту команду.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    # Определяем цвет Embed в зависимости от типа
    color = discord.Color.green()  # по умолчанию для сходок
    if meeting_type.value == "NEWS":
        color = discord.Color.gold()

    # Создаём Embed
    embed = discord.Embed(
        title=f"{meeting_type.name}",
        description=custom_text,
        color=color
    )
    embed.set_footer(text=f"Для роли: {role.name}")

    sent_count = 0
    failed_count = 0

    # Отправляем Embed в ЛС каждому участнику роли
    for member in role.members:
        try:
            await member.send(embed=embed)
            sent_count += 1
        except:
            failed_count += 1

    await interaction.followup.send(
        f"✅ Сообщения отправлены: {sent_count}\n⚠ Не удалось отправить: {failed_count}",
        ephemeral=True
    )





# -------------------- ЗАПУСК --------------------
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN не найден! Установите его в .env или переменных окружения.")
    print("Запуск бота...")
    bot.run(token)


import signal
import sys
import asyncio

# 🛡 Корректное завершение при остановке контейнера (Kill / Stop на хостинге)
def shutdown_handler(sig, frame):
    print("🛑 Получен сигнал остановки от хостинга...")

    try:
        loop = asyncio.get_event_loop()

        async def shutdown():
            print("⏳ Завершаем соединение с Discord...")
            await bot.close()
            print("✅ Бот успешно завершён.")
            sys.exit(0)

        # Проверяем, запущен ли цикл
        if loop.is_running():
            loop.create_task(shutdown())
        else:
            loop.run_until_complete(shutdown())

    except Exception as e:
        print(f"⚠️ Ошибка при завершении: {e}")
        sys.exit(1)

# Регистрируем сигналы остановки контейнера
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# 🧠 Keep-alive — чтобы Wisbyte не думал, что бот "завис"
async def keep_alive():
    while True:
        await asyncio.sleep(60)
        print("✅ Проверка активности — бот работает стабильно")

# Запускаем фоновую задачу через цикл, если бот уже запущен
try:
    loop = asyncio.get_event_loop()
    loop.create_task(keep_alive())
except Exception as e:
    print(f"⚠️ Не удалось запустить keep_alive: {e}")