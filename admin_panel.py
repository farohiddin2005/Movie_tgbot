from aiogram import Bot, types
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
import psycopg2
from dotenv import load_dotenv
import os
from urllib.parse import urlparse

load_dotenv()
# Admin ID’larini .env dan olish
admin_ids_str = os.getenv("ADMIN_IDS", "5358180855")  # Standart qiymat sifatida bitta ID
ADMINS = [int(id.strip()) for id in admin_ids_str.split(',')]  # Vergul bilan ajratilgan ID’lar ro‘yxatini olish

async def admin_check(message: Message, bot: Bot, state: FSMContext) -> bool:
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.reply("*❌ Sizda admin huquqlari yo'q!*\n\nFaqat adminlar ushbu opsiyalardan foydalanishi mumkin.", parse_mode="Markdown")
        return False
    return True

# Kino qo'shish (yangi: link va nom bilan)
async def add_movie(message: Message, bot: Bot, state: FSMContext, movie_name: str, movie_link: str):
    if not await admin_check(message, bot, state):
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        await message.reply("*❌ Ma'lumotlar bazasi ulanishi topilmadi!*\n\nRailway’dagi DATABASE_URL’ni tekshirib ko‘ring.", parse_mode="Markdown")
        return
    
    url = urlparse(db_url)
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode='require'
    )
    cursor = conn.cursor()
    cursor.execute("INSERT INTO movies (name, link) VALUES (%s, %s) RETURNING id", (movie_name, movie_link))
    movie_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    await message.reply(f"*🎬 Kino muvaffaqiyatli qo'shildi! Nom: {movie_name} | Link: {movie_link}*\n\nRahmat, yangi kino uchun! 🎥", parse_mode="Markdown")

# Kino tahrirlash (yangi: /edit_movie’siz)
async def edit_movie(message: Message, bot: Bot, state: FSMContext, movie_id: str, new_value: str):
    if not await admin_check(message, bot, state):
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        await message.reply("*❌ Ma'lumotlar bazasi ulanishi topilmadi!*\n\nRailway’dagi DATABASE_URL’ni tekshirib ko‘ring.", parse_mode="Markdown")
        return
    
    url = urlparse(db_url)
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode='require'
    )
    cursor = conn.cursor()
    cursor.execute("UPDATE movies SET name = %s WHERE id = %s", (new_value, movie_id))
    if cursor.rowcount == 0:
        cursor.execute("UPDATE movies SET link = %s WHERE id = %s", (new_value, movie_id))
    conn.commit()
    conn.close()

    await message.reply(f"*✏️ Kino (ID: {movie_id}) muvaffaqiyatli tahrirlandi!*\n\nYangi qiymat: *{new_value}*", parse_mode="Markdown")

# Kino o'chirish (yangi: /delete_movie’siz)
async def delete_movie(message: Message, bot: Bot, state: FSMContext, movie_id: str):
    if not await admin_check(message, bot, state):
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        await message.reply("*❌ Ma'lumotlar bazasi ulanishi topilmadi!*\n\nRailway’dagi DATABASE_URL’ni tekshirib ko‘ring.", parse_mode="Markdown")
        return
    
    url = urlparse(db_url)
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode='require'
    )
    cursor = conn.cursor()
    cursor.execute("DELETE FROM movies WHERE id = %s", (movie_id,))
    conn.commit()
    conn.close()

    await message.reply(f"*🗑️ Kino (ID: {movie_id}) muvaffaqiyatli o'chirildi!*\n\nRahmat, buni uchun!", parse_mode="Markdown")

# Reklamma kanal qo'shish/o'zgartirish (yangi: nom, ID va link bilan, ma'lumotlar bazasiga saqlash)
async def set_channel(message: Message, bot: Bot, state: FSMContext, channel_name: str, channel_id: str, channel_link: str):
    if not await admin_check(message, bot, state):
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        await message.reply("*❌ Ma'lumotlar bazasi ulanishi topilmadi!*\n\nRailway’dagi DATABASE_URL’ni tekshirib ko‘ring.", parse_mode="Markdown")
        return
    
    url = urlparse(db_url)
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode='require'
    )
    cursor = conn.cursor()
    cursor.execute("INSERT INTO advertisement_channels (name, id, link) VALUES (%s, %s, %s) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, link = EXCLUDED.link", (channel_name, channel_id, channel_link))
    conn.commit()
    conn.close()

    await message.reply(f"*🌐 Reklamma kanal muvaffaqiyatli qo'shildi! Nom: {channel_name} | ID: {channel_id} | Link: {channel_link}*\n\nKanalni tekshirib ko‘ring!", parse_mode="Markdown")

# Reklamma kanal o'chirish
async def delete_channel(message: Message, bot: Bot, state: FSMContext, channel_id: str):
    if not await admin_check(message, bot, state):
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        await message.reply("*❌ Ma'lumotlar bazasi ulanishi topilmadi!*\n\nRailway’dagi DATABASE_URL’ni tekshirib ko‘ring.", parse_mode="Markdown")
        return
    
    url = urlparse(db_url)
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode='require'
    )
    cursor = conn.cursor()
    cursor.execute("DELETE FROM advertisement_channels WHERE id = %s", (channel_id,))
    conn.commit()
    conn.close()

    await message.reply(f"*🗑️ Reklamma kanal {channel_id} muvaffaqiyatli o'chirildi!*\n\nKanal ma'lumotlar bazasidan o‘chirildi.", parse_mode="Markdown")

# Reklamma kanal tahrirlash
async def edit_channel(message: Message, bot: Bot, state: FSMContext, old_channel_id: str, new_channel_id: str):
    if not await admin_check(message, bot, state):
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        await message.reply("*❌ Ma'lumotlar bazasi ulanishi topilmadi!*\n\nRailway’dagi DATABASE_URL’ni tekshirib ko‘ring.", parse_mode="Markdown")
        return
    
    url = urlparse(db_url)
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode='require'
    )
    cursor = conn.cursor()
    cursor.execute("UPDATE advertisement_channels SET id = %s WHERE id = %s", (new_channel_id, old_channel_id))
    if cursor.rowcount == 0:
        await message.reply("*❌ Bunday reklamma kanal topilmadi!*\n\nEski kanal ID’sini qayta tekshirib ko‘ring.", parse_mode="Markdown")
        conn.close()
        return
    # Yangi ID uchun nom va linkni yangilash uchun qo‘shimcha so‘rov (agar kerak bo‘lsa)
    cursor.execute("SELECT name, link FROM advertisement_channels WHERE id = %s", (new_channel_id,))
    channel = cursor.fetchone()
    if channel:
        name, link = channel
        await message.answer(f"*✏️ Reklamma kanal {old_channel_id} yangi ID {new_channel_id} bilan muvaffaqiyatli tahrirlandi!*\n\nNom: {name} | Link: {link}", parse_mode="Markdown")
    else:
        await message.answer(f"*✏️ Reklamma kanal {old_channel_id} yangi ID {new_channel_id} bilan muvaffaqiyatli tahrirlandi!*\n\nKanal ma'lumotlarini yangilang.", parse_mode="Markdown")
    conn.commit()
    conn.close()