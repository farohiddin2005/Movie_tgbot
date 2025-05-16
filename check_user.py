from aiogram import Bot, types
from aiogram.types import Update, Message
from aiogram.fsm.context import FSMContext
from typing import Union
import os
import psycopg2
from urllib.parse import urlparse

# Global o‘zgaruvchi sifatida kanal ID’sini saqlash
CHANNEL_ID = os.getenv("CHANNEL_ID", "@DefaultChannel")  # .env dan olish mumkin

# Admin ID’larini .env dan olish
admin_ids_str = os.getenv("ADMIN_IDS", "5358180855")  # Standart qiymat sifatida bitta ID
ADMINS = [int(id.strip()) for id in admin_ids_str.split(',')]  # Vergul bilan ajratilgan ID’lar ro‘yxatini olish

async def check_membership(update: Union[Update, types.Message], bot: Bot, state: Union[FSMContext, None] = None, channel_id: str = None) -> bool:
    user_id = update.from_user.id if isinstance(update, (Update, types.Message)) else update.from_user.id
    # .env yoki funksiyaga o‘tgan kanal ID’sini olish
    if channel_id is None:
        channel_id = CHANNEL_ID
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        else:
            if isinstance(update, types.Message):
                await update.reply(
                    f"*❌ Iltimos, avval {channel_id} reklamma kanaliga a'zo bo'ling!*\n\nKanalga a'zo bo‘lganingizdan keyin bot bilan davom eting! 🚀", parse_mode="Markdown"
                )
            return False
    except Exception as e:
        if isinstance(update, types.Message):
            await update.reply("*⚠️ Xatolik yuz berdi. Kanalni tekshirib ko'ring.*\n\nBot bilan aloqada muammolar bo‘lishi mumkin, loglarni tekshiring.", parse_mode="Markdown")
        return False

# Ma'lumotlar bazasidan reklamma kanallarni olish funksiyasi
async def get_channels_from_db(bot: Bot) -> list:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return []

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
    cursor.execute("SELECT id FROM advertisement_channels")
    channels = [row[0] for row in cursor.fetchall()]
    conn.close()
    return channels