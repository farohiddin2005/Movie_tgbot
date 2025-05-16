from aiogram import Bot, types
from aiogram.types import Update, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from check_user import check_membership
from typing import Union

class MovieStates(StatesGroup):
    waiting_for_movie_id = State()

async def request_movie(update: Union[Update, Message], bot: Bot, state: FSMContext):
    if not await check_membership(update, bot, state):
        return

    if isinstance(update, Message):
        await update.reply("*🎬 Iltimos, kino ID’sini kiriting:*\n\nMasalan: *123* — bu kino ID’si bo‘lishi mumkin!", parse_mode="Markdown")
    else:
        await update.message.reply("*🎬 Iltimos, kino ID’sini kiriting:*\n\nMasalan: *123* — bu kino ID’si bo‘lishi mumkin!", parse_mode="Markdown")
    await state.set_state(MovieStates.waiting_for_movie_id)