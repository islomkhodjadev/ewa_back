# handlers/profile.py
from aiogram import types, Bot, Router, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from telegram_client.models import BotClient
from .handle_start_flow import give_parent_tree

profile_router = Router()  # <— Роутер профиля

BACK_BTN = "⬅️ Назад"
EXIT_BTN = "🚪 Выйти из профиля"
CONFIRM_EXIT_BTN = "✅ Да, выйти"
CANCEL_EXIT_BTN = "❌ Отмена"
ASSISTANT_BTN = "Виртуальный помощник"  # ← удобно в константу


class ProfileSG(StatesGroup):
    viewing = State()
    confirm_exit = State()


def profile_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[KeyboardButton(text=BACK_BTN), KeyboardButton(text=EXIT_BTN)]],
    )


def confirm_exit_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text=CONFIRM_EXIT_BTN)],
            [KeyboardButton(text=CANCEL_EXIT_BTN)],
        ],
    )


def back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[KeyboardButton(text=BACK_BTN)]],
    )


def format_profile_text(c: BotClient) -> str:
    full_name_parts = [c.last_name, c.first_name]
    full_name = " ".join(p for p in full_name_parts if p) or (
        f"@{c.username}" if c.username else "—"
    )
    phone = c.phone_number or "—"
    return f"Личный кабинет\nФИО: {full_name}\nНомер телефона: {phone}"


# ... (клавиатуры и format_profile_text без изменений)


@profile_router.message(F.text == "Личный кабинет")
async def enter_profile(message: types.Message, bot: Bot, state: FSMContext):
    bot_client = await BotClient.objects.filter(chat_id=message.from_user.id).afirst()
    if not bot_client:
        await state.clear()
        return await message.answer(
            "Похоже, вы ещё не зарегистрированы.", reply_markup=ReplyKeyboardRemove()
        )
    await state.set_state(ProfileSG.viewing)
    return await message.answer(
        format_profile_text(bot_client), reply_markup=profile_keyboard()
    )


# === ТОЧЕЧНЫЕ ХЕНДЛЕРЫ ВНУТРИ viewing ===


@profile_router.message(ProfileSG.viewing, F.text == BACK_BTN)
async def profile_back(message: types.Message, bot: Bot, state: FSMContext):
    await state.clear()
    return await give_parent_tree(message, bot, True)


@profile_router.message(ProfileSG.viewing, F.text == EXIT_BTN)
async def profile_exit(message: types.Message, bot: Bot, state: FSMContext):
    await state.set_state(ProfileSG.confirm_exit)
    return await message.answer(
        "Выйти из профиля? Данные сохранятся, но для доступа потребуется повторный вход.",
        reply_markup=confirm_exit_keyboard(),
    )


# Если пользователь нажал «Виртуальный помощник» из профиля — выходим из профиля и передаём дальше
@profile_router.message(
    ProfileSG.viewing, F.text == ASSISTANT_BTN, flags={"block": False}
)
async def profile_to_assistant(message: types.Message, bot: Bot, state: FSMContext):
    await state.clear()
    # ничего не отвечаем — пусть следующий роутер обработает кнопку «Виртуальный помощник»


# Catch-all в viewing: очищаем состояние и пропускаем дальше
@profile_router.message(ProfileSG.viewing, flags={"block": False})
async def profile_passthrough(message: types.Message, bot: Bot, state: FSMContext):
    await state.clear()
    # не отвечаем, чтобы следующий хендлер (например, дерево) отработал


# === confirm_exit ===


@profile_router.message(ProfileSG.confirm_exit, F.text == CONFIRM_EXIT_BTN)
async def confirm_exit(message: types.Message, bot: Bot, state: FSMContext):
    bot_client = await BotClient.objects.filter(chat_id=message.from_user.id).afirst()
    if bot_client:
        await BotClient.objects.filter(pk=bot_client.pk).aupdate(is_logined=False)
    await state.clear()
    return await message.answer(
        "Вы вышли из аккаунта, нажмите кнопку /start, чтобы начать работу",
        reply_markup=ReplyKeyboardRemove(),
    )


@profile_router.message(ProfileSG.confirm_exit, F.text == CANCEL_EXIT_BTN)
async def cancel_exit(message: types.Message, bot: Bot, state: FSMContext):
    bot_client = await BotClient.objects.filter(chat_id=message.from_user.id).afirst()
    await state.set_state(ProfileSG.viewing)
    return await message.answer(
        format_profile_text(bot_client), reply_markup=profile_keyboard()
    )
