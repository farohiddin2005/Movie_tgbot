from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from movie_request import request_movie, MovieStates
from send_movie import send_movie
from admin_panel import add_movie, edit_movie, delete_movie, set_channel, delete_channel, edit_channel
from database import init_db
from aiogram.filters import Command
from check_user import check_membership, get_channels_from_db
from aiogram.fsm.context import FSMContext
from typing import Union
import os
from dotenv import load_dotenv
import psycopg2
from urllib.parse import urlparse
import asyncio
import logging

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Ma'lumotlar bazasini ishga tushirish
try:
    init_db()
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    raise

bot = Bot(token=os.getenv("BOT_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Global o‘zgaruvchi sifatida kanal ID’sini saqlash
CHANNEL_ID = os.getenv("CHANNEL_ID", "@DefaultChannel")  # .env dan olish mumkin

# Admin ID’larini .env dan olish
admin_ids_str = os.getenv("ADMIN_IDS", "5358180855")  # Standart qiymat sifatida bitta ID
ADMINS = [int(id.strip()) for id in admin_ids_str.split(',')]  # Vergul bilan ajratilgan ID’lar ro‘yxatini olish

# Yangi davlatlar (states) aniqlash
class AdminStates(StatesGroup):
    waiting_for_movie_link = State()
    waiting_for_movie_name = State()
    waiting_for_movie_id = State()  # Kino ID’si uchun (tahrirlash/o‘chirish)
    waiting_for_movie_new_value = State()  # Yangi qiymat uchun (tahrirlash)
    waiting_for_channel_name = State()  # Kanal nomi uchun
    waiting_for_channel_id = State()  # Kanal ID’si uchun
    waiting_for_channel_link = State()  # Kanal linki uchun
    waiting_for_delete_channel = State()
    waiting_for_edit_channel = State()
    waiting_for_delete_movie = State()  # Kino o‘chirish uchun yangi davlat

class UserStates(StatesGroup):
    waiting_for_movie_id = State()  # Foydalanuvchi uchun kino ID’si

# Kinolar ro‘yxatini olish funksiyasi
async def get_movies_list(bot: Bot, user_id: int):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return "Ma'lumotlar bazasi ulanishi topilmadi!"

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
    cursor.execute("SELECT id, name, link FROM movies")
    movies = cursor.fetchall()
    conn.close()

    if not movies:
        return "Hozircha hech qanday kino mavjud emas!"

    response = "🎥 *Kinolar Ro‘yxati:*\n"
    for movie in movies:
        response += f"📌 ID: `{movie[0]}` | Nom: *{movie[1]}* | Link: `{movie[2]}`\n"
    return response

# Reklamma kanallarni olish funksiyasi (ma'lumotlar bazasidan)
async def get_advertisement_channels_list(bot: Bot) -> list:
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
    cursor.execute("SELECT name, id, link FROM advertisement_channels")
    channels = cursor.fetchall()
    conn.close()

    return channels  # Hamma kanal ma'lumotlarini (nom, ID, link) qaytaradi

# /start komandasiga javob (foydalanuvchi uchun salomlashish va ma'lumotlar bazasidagi reklamma kanallari ro‘yxati)
@dp.message(Command(commands=["start"]))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in ADMINS:
        # Admin uchun estetik inline button'lar
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🎬 Kino Qo'shish", callback_data="add_movie"),
                types.InlineKeyboardButton(text="✏️ Kino Tahrirlash", callback_data="edit_movie")
            ],
            [
                types.InlineKeyboardButton(text="🗑️ Kino O'chirish", callback_data="delete_movie"),
                types.InlineKeyboardButton(text="👀 Kinolar Ro‘yxati", callback_data="view_movies")
            ],
            [
                types.InlineKeyboardButton(text="🌐 Kanal Qo'shish", callback_data="set_channel"),
                types.InlineKeyboardButton(text="🗑️ Kanal O'chirish", callback_data="delete_channel")
            ],
            [
                types.InlineKeyboardButton(text="✏️ Kanal Tahrirlash", callback_data="edit_channel"),
                types.InlineKeyboardButton(text="🌐 Kanallar Ro‘yxati", callback_data="view_channels")
            ]
        ])
        await message.answer("*Salom, Admin! Quyidagi opsiyalardan birini tanlang:*\n\nBotim bilan ishlayotganingizdan xursandman! 🎉", reply_markup=keyboard, parse_mode="Markdown")
    else:
        # Oddiy foydalanuvchi uchun salomlashish va ma'lumotlar bazasidagi reklamma kanallari ro‘yxati
        await message.answer("*Salom, hurmatli foydalanuvchi! Men kino botiman. Avval reklamma kanallarga a'zo bo'ling!*\n\nBotim bilan tanishganingizdan xursandman! 🌟", parse_mode="Markdown")
        channels = await get_advertisement_channels_list(bot)
        if not channels:
            await message.answer("*⚠️ Hozircha hech qanday reklamma kanal mavjud emas!*\n\nAdmin bilan bog‘laning yoki kanallarni qo‘shing.", parse_mode="Markdown")
            return

        # Foydalanuvchining a’zoligini tekshirish
        channel_ids = [channel[1] for channel in channels]  # Faqat ID’lar ro‘yxatini olish
        membership_results = await asyncio.gather(*[check_membership(message, bot, None, channel_id) for channel_id in channel_ids])
        non_member_channels = [channel for i, channel in enumerate(channels) if not membership_results[i]]

        if not non_member_channels:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🌐 Kanallar Ro‘yxati", callback_data="view_channels")]
            ])
            await message.answer("*✅ Siz barcha zarur reklamma kanallarga a'zo ekansiz! Kino so‘rov qilish uchun kino ID’sini kiriting:*\n\nMenga yordam berish uchun kanalga a'zo bo‘ling! 🎥", reply_markup=keyboard, parse_mode="Markdown")
            await state.set_state(UserStates.waiting_for_movie_id)  # Foydalanuvchi uchun kino ID’si davlati
        else:
            # Faqat a’zo bo‘lmagan reklamma kanallarni button’lar bilan ko‘rsatish
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=f"📋 Kanal: {channel[0]}", url=channel[2] if channel[2].startswith("https://t.me/") else f"https://t.me/{channel[1].replace('@', '') if channel[1].startswith('@') else channel[1]}")]
                for channel in non_member_channels
            ] + [[types.InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_membership")]])
            await message.answer("*Iltimos, quyidagi reklamma kanallarga a'zo bo'ling, keyin “Tekshirish” tugmasini bosing!*\n\nKanalga a'zo bo‘lganingizdan keyin men bilan davom eting! 🚀", reply_markup=keyboard, parse_mode="Markdown")

# Callback handler’lar (foydalanuvchi uchun tekshirish)
@dp.callback_query(lambda c: c.data == "check_membership")
async def process_check_membership(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    message = callback_query.message

    # Ma'lumotlar bazasidan reklamma kanallarni olish
    channels = await get_advertisement_channels_list(bot)
    if not channels:
        await message.answer("*⚠️ Hozircha hech qanday reklamma kanal mavjud emas!*\n\nAdmin bilan bog‘laning yoki kanallarni qo‘shing.", parse_mode="Markdown")
        return

    # Asinxron chaqiruvlarni to‘g‘ri boshqarish
    channel_ids = [channel[1] for channel in channels]  # Faqat ID’lar ro‘yxatini olish
    membership_results = await asyncio.gather(*[check_membership(message, bot, None, channel_id) for channel_id in channel_ids])
    if all(membership_results):
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🌐 Kanallar Ro‘yxati", callback_data="view_channels")]
        ])
        await message.answer("*✅ Siz barcha zarur reklamma kanallarga a'zo ekansiz! Kino so‘rov qilish uchun kino ID’sini kiriting:*\n\nMenga yordam berish uchun kanalga a'zo bo‘ling! 🎥", reply_markup=keyboard, parse_mode="Markdown")
        await state.set_state(UserStates.waiting_for_movie_id)  # Foydalanuvchi uchun kino ID’si davlati
    else:
        # Faqat a’zo bo‘lmagan reklamma kanallarni button’lar bilan qayta ko‘rsatish
        non_member_channels = [channel for i, channel in enumerate(channels) if not membership_results[i]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=f"📋 Kanal: {channel[0]}", url=channel[2] if channel[2].startswith("https://t.me/") else f"https://t.me/{channel[1].replace('@', '') if channel[1].startswith('@') else channel[1]}")]
            for channel in non_member_channels
        ] + [[types.InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_membership")]])
        await message.answer("*❌ Siz hali barcha reklamma kanallarga a'zo emassiz! Iltimos, quyidagi kanallarga a'zo bo'ling, keyin qayta tekshiring!*\n\nKanalga a'zo bo‘lganingizdan keyin men bilan davom eting! 🚀", reply_markup=keyboard, parse_mode="Markdown")

# Callback handler'lar admin uchun
@dp.callback_query(lambda c: c.data == "add_movie")
async def process_add_movie(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "*🎬 Kino manzilini (boshqa kanaldan link sifatida) kiriting:*\n\nMasalan: *https://t.me/example_channel/123*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_movie_link)

@dp.callback_query(lambda c: c.data == "edit_movie")
async def process_edit_movie(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "*✏️ Kino ID’sini kiriting:*\n\nMasalan: *1*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_movie_id)

@dp.callback_query(lambda c: c.data == "delete_movie")
async def process_delete_movie(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "*🗑️ O'chirish uchun kino ID’sini kiriting:*\n\nMasalan: *1*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_delete_movie)

@dp.callback_query(lambda c: c.data == "set_channel")
async def process_set_channel(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "*🌐 Kanal nomini kiriting:*\n\nMasalan: *Kino PRIME*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_channel_name)

@dp.callback_query(lambda c: c.data == "delete_channel")
async def process_delete_channel(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "*🗑️ O'chirish uchun kanal ID’sini kiriting:*\n\nMasalan: *@example_channel* yoki *-1001234567890*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_delete_channel)

@dp.callback_query(lambda c: c.data == "edit_channel")
async def process_edit_channel(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "*✏️ Kanal ID va yangi kanal ID’sini kiriting (format: <eski_ID> <yangi_ID>):*\n\nMasalan: *@old_channel @new_channel*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_edit_channel)

@dp.callback_query(lambda c: c.data == "view_movies")
async def process_view_movies(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    movies_list = await get_movies_list(bot, callback_query.from_user.id)
    await bot.send_message(callback_query.from_user.id, movies_list, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "view_channels")
async def process_view_channels(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    channels_list = await get_advertisement_channels_list(bot)
    response = "🌐 *Reklamma Kanallar Ro‘yxati:*\n" + "\n".join([f"📋 Nom: *{channel[0]}* | ID: `{channel[1]}` | Link: *{channel[2]}*" for channel in channels_list])
    await bot.send_message(callback_query.from_user.id, response, parse_mode="Markdown")

# Admin uchun yangi handler'lar
@dp.message(AdminStates.waiting_for_channel_name, lambda message: message.from_user.id in ADMINS)
async def handle_channel_name(message: Message, state: FSMContext):
    channel_name = message.text
    if not channel_name:
        await message.answer("*❌ Iltimos, to‘g‘ri kanal nomini kiriting!*\n\nMasalan: *Kino PRIME*", parse_mode="Markdown")
        return
    await state.update_data(channel_name=channel_name)
    await message.answer("*🌐 Kanal ID’sini kiriting:*\n\nMasalan: *@example_channel* yoki *-1001234567890*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_channel_id)

@dp.message(AdminStates.waiting_for_channel_id, lambda message: message.from_user.id in ADMINS)
async def handle_channel_id(message: Message, state: FSMContext):
    channel_id = message.text
    if not (channel_id.startswith('@') or channel_id.startswith('-100')):
        await message.answer("*❌ Iltimos, to‘g‘ri kanal ID’sini kiriting!*\n\nMasalan: *@example_channel* yoki *-1001234567890*", parse_mode="Markdown")
        await state.clear()
        return
    await state.update_data(channel_id=channel_id)
    await message.answer("*🌐 Kanal linkini kiriting:*\n\nMasalan: *https://t.me/example_channel*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_channel_link)

@dp.message(AdminStates.waiting_for_channel_link, lambda message: message.from_user.id in ADMINS)
async def handle_channel_link(message: Message, state: FSMContext):
    channel_link = message.text
    if not channel_link.startswith("https://t.me/"):
        await message.answer("*❌ Iltimos, to‘g‘ri kanal linkini kiriting!*\n\nMasalan: *https://t.me/example_channel*", parse_mode="Markdown")
        await state.clear()
        return
    user_data = await state.get_data()
    channel_name = user_data.get("channel_name")
    channel_id = user_data.get("channel_id")
    if not channel_name or not channel_id or not channel_link:
        await message.answer("*❌ Kanal nomi, ID yoki linki kiritilmagan!*\n\nQayta urinib ko‘ring.", parse_mode="Markdown")
        await state.clear()
        return
    await set_channel(message, bot, state, channel_name, channel_id, channel_link)
    global CHANNEL_ID
    CHANNEL_ID = channel_id
    await message.answer(f"*🌐 Kanal muvaffaqiyatli qo'shildi! Nom: {channel_name} | ID: {channel_id} | Link: {channel_link}*\n\nKanalni tekshirib ko‘ring!", parse_mode="Markdown")
    await state.clear()

@dp.message(AdminStates.waiting_for_movie_link, lambda message: message.from_user.id in ADMINS)
async def handle_movie_link(message: Message, state: FSMContext):
    movie_link = message.text
    if not movie_link.startswith("https://t.me/"):
        await message.answer("*❌ Iltimos, to‘g‘ri kino manzilini (link) kiriting!*\n\nMasalan: *https://t.me/example_channel/123*", parse_mode="Markdown")
        return
    await state.update_data(movie_link=movie_link)
    await message.answer("*📎 Kino nomini kiriting:*\n\nMasalan: *Qahramonlar Filmi*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_movie_name)

@dp.message(AdminStates.waiting_for_movie_name, lambda message: message.from_user.id in ADMINS)
async def handle_movie_name(message: Message, state: FSMContext):
    movie_name = message.text
    user_data = await state.get_data()
    movie_link = user_data.get("movie_link")
    if not movie_name or not movie_link:
        await message.answer("*❌ Kino nomi yoki manzili kiritilmagan!*\n\nQayta urinib ko‘ring.", parse_mode="Markdown")
        await state.clear()
        return
    await add_movie(message, bot, state, movie_name, movie_link)
    await message.answer(f"*🎬 Kino muvaffaqiyatli qo'shildi! Nom: {movie_name} | Link: {movie_link}*\n\nRahmat, yangi kino uchun! 🎥", parse_mode="Markdown")
    await state.clear()

@dp.message(AdminStates.waiting_for_movie_id, lambda message: message.from_user.id in ADMINS)
async def handle_movie_id_for_edit(message: Message, state: FSMContext):
    movie_id = message.text
    if not movie_id.isdigit():
        await message.answer("*❌ Iltimos, to‘g‘ri kino ID’sini kiriting!*\n\nMasalan: *1*", parse_mode="Markdown")
        await state.clear()
        return
    await state.update_data(movie_id=movie_id)
    await message.answer("*✏️ Yangi nom yoki linkni kiriting:*\n\nMasalan: *Yangi Kino* yoki *https://t.me/example_channel/123*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_movie_new_value)

@dp.message(AdminStates.waiting_for_movie_new_value, lambda message: message.from_user.id in ADMINS)
async def handle_movie_new_value(message: Message, state: FSMContext):
    new_value = message.text
    user_data = await state.get_data()
    movie_id = user_data.get("movie_id")
    if not movie_id or not new_value:
        await message.answer("*❌ Kino ID yoki yangi qiymat kiritilmagan!*\n\nQayta urinib ko‘ring.", parse_mode="Markdown")
        await state.clear()
        return
    await edit_movie(message, bot, state, movie_id, new_value)
    await message.answer(f"*✏️ Kino (ID: {movie_id}) muvaffaqiyatli tahrirlandi!*\n\nYangi qiymat: *{new_value}*", parse_mode="Markdown")
    await state.clear()

@dp.message(AdminStates.waiting_for_delete_movie, lambda message: message.from_user.id in ADMINS)
async def handle_delete_movie(message: Message, state: FSMContext):
    movie_id = message.text
    if not movie_id.isdigit():
        await message.answer("*❌ Iltimos, to‘g‘ri kino ID’sini kiriting!*\n\nMasalan: *1*", parse_mode="Markdown")
        await state.clear()
        return
    await delete_movie(message, bot, state, movie_id)
    await message.answer(f"*🗑️ Kino (ID: {movie_id}) muvaffaqiyatli o'chirildi!*\n\nRahmat, buni uchun!", parse_mode="Markdown")
    await state.clear()

@dp.message(AdminStates.waiting_for_delete_channel, lambda message: message.from_user.id in ADMINS)
async def handle_delete_channel(message: Message, state: FSMContext):
    channel_id = message.text
    if not (channel_id.startswith('@') or channel_id.startswith('-100')):
        await message.answer("*❌ Iltimos, to‘g‘ri kanal ID’sini kiriting!*\n\nMasalan: *@example_channel* yoki *-1001234567890*", parse_mode="Markdown")
        await state.clear()
        return
    await delete_channel(message, bot, state, channel_id)
    global CHANNEL_ID
    if CHANNEL_ID == channel_id:
        CHANNEL_ID = "@DefaultChannel"
        await message.answer(f"*🗑️ Kanal {channel_id} muvaffaqiyatli o'chirildi!*\n\nStandart kanalga qaytdik: @DefaultChannel*", parse_mode="Markdown")
    else:
        await message.answer("*❌ Bunday kanal topilmadi!*\n\nKanal ID’sini qayta tekshirib ko‘ring.", parse_mode="Markdown")
    await state.clear()

@dp.message(AdminStates.waiting_for_edit_channel, lambda message: message.from_user.id in ADMINS)
async def handle_edit_channel(message: Message, state: FSMContext):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("*❌ Iltimos, <eski_ID> <yangi_ID> kiriting!*\n\nMasalan: *@old_channel @new_channel*", parse_mode="Markdown")
        await state.clear()
        return
    old_channel_id, new_channel_id = args[0], args[1]
    if not (old_channel_id.startswith('@') or old_channel_id.startswith('-100')) or not (new_channel_id.startswith('@') or new_channel_id.startswith('-100')):
        await message.answer("*❌ Iltimos, to‘g‘ri kanal ID’larini kiriting!*\n\nMasalan: *@old_channel @new_channel*", parse_mode="Markdown")
        await state.clear()
        return
    await edit_channel(message, bot, state, old_channel_id, new_channel_id)
    global CHANNEL_ID
    if CHANNEL_ID == old_channel_id:
        CHANNEL_ID = new_channel_id
        await message.answer(f"*✏️ Kanal {old_channel_id} yangi ID {new_channel_id} bilan muvaffaqiyatli tahrirlandi!*\n\nKanalni tekshirib ko‘ring!", parse_mode="Markdown")
    else:
        await message.answer("*❌ Bunday kanal topilmadi!*\n\nEski kanal ID’sini qayta tekshirib ko‘ring.", parse_mode="Markdown")
    await state.clear()

# Foydalanuvchi va admin uchun kino ID’si handler’i (doimiy ravishda ishlaydi)
@dp.message(UserStates.waiting_for_movie_id, lambda message: True)  # Har bir foydalanuvchi uchun, admin ham
async def handle_movie_id(message: Message, state: FSMContext):
    movie_id = message.text
    if not movie_id.isdigit():
        await message.answer("*❌ Iltimos, to‘g‘ri kino ID’sini kiriting!*\n\nMasalan: *1*", parse_mode="Markdown")
        return
    try:
        await send_movie(message, bot, state, movie_id)
        # Davlatni to‘g‘ri saqlash uchun clear qilmasdan qoldiraman, shunda foydalanuvchi keyingi ID’larni yuborishi mumkin
    except Exception as e:
        logger.error(f"Error sending movie with ID {movie_id}: {e}")
        await message.answer("*❌ Kino yuborishda xatolik yuz berdi! Iltimos, ID’ni qayta tekshirib ko‘ring yoki admin bilan bog‘laning.*", parse_mode="Markdown")
        await state.clear()  # Xatolik bo‘lganda davlatni tozalash

# Handler'lar
dp.message.register(request_movie, Command(commands=["get_movie"]))
dp.message.register(add_movie, Command(commands=["add_movie"]))
dp.message.register(edit_movie, Command(commands=["edit_movie"]))
dp.message.register(delete_movie, Command(commands=["delete_movie"]))
dp.message.register(set_channel, Command(commands=["set_channel"]))

if __name__ == "__main__":
    dp.run_polling(bot)