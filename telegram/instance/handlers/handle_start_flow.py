from aiogram import types, Bot, Router, F
from aiogram.filters import CommandStart
from aiogram.fsm import context

from telegram_client.models import BotClient
from telegram.instance.states import LoginFSM
from telegram.instance.utils import login_post, fill_and_activate_user
from telegram.instance.markup_buttons import (
    InlineButton,
    inline_markup_builder,
    reply_markup_builder,
    ReplyButton,
)
from .handle_tree_markups import give_parent_tree

start_flow_router = Router()


async def start(message: types.Message, bot: Bot, state: context.FSMContext) -> None:

    user = message.from_user

    bot_client, created = await BotClient.objects.aupdate_or_create(
        chat_id=message.chat.id,
        username=user.username,
    )
    if created:
        bot_client.aupdate_fields(
            first_name=user.first_name,
            last_name=user.last_name,
        )

    await state.set_state(LoginFSM.access_parameter)

    await message.answer(
        "Добро пожаловать, для продолжения работы нужно авторизоваться \n "
        "Пожалуйста, отправьте логин, который вы указывали прирегистрации на сайте https://ewaproduct.com/ru"
    )
    await message.delete()


async def get_login_access_parameter(
    message: types.Message, bot: Bot, state: context.FSMContext
) -> None:
    await state.update_data(access_parameter=message.text)

    await state.set_state(LoginFSM.password)
    await message.answer("Введите пароль от аккаунта")
    await message.delete()


async def get_login_password(
    message: types.Message, bot: Bot, state: context.FSMContext
):
    await state.update_data(password=message.text)

    data = await state.get_data()
    await state.clear()

    status_code, response_data = await login_post(
        access_parameter=data["access_parameter"], password=data["password"]
    )

    if status_code == 200:
        first_name, last_name = await fill_and_activate_user(
            response_data, message.from_user.id
        )
        start_button = inline_markup_builder(
            [InlineButton(text="start", callback_data="start")]
        )
        await message.answer(
            f"Добро пожаловать, {last_name}  {first_name}!"
            "Я – EWA_assistant AI, твой персональный AI – ассистент в партнерстве с EWA PRODUCT.\n"
            "Не пью кофе, не устаю и не ухожу в отпуск – всегда на связи, что бы прокачать тебя в продукте и бизнесе.\n"
            "Нужны ответы быстро и по делу? – уже бегу!\n"
            "А, перед началом нашей беседы, предлагаю тебе ответить на пару вопросов, что бы я лучше узнал тебя!",
            reply_markup=start_button,
        )

    else:
        await message.answer(
            "Вы не зарегистрированы на сайте, перейдите по ссылке и зарегистрируйтесь: https://ewaproduct.com/ru"
            "после отправьте логин, который вы указывали прирегистрации"
        )
        await state.set_state(LoginFSM.access_parameter)

    await message.delete()


STAGE1 = {"Уже работаю", "Планирую начать", "Изучаю варианты"}
STAGE2 = {"Нет опыта", "Менее года", "1-3 года", "Более 3-х лет"}
STAGE3 = {
    "Дополнительный доход",
    "Развитие офлайн - бизнеса",
    "Выход на пассив",
    "Построение команды",
    "Развитие личного бренда",
    "Развитие онлайн - бизнеса",
}
STAGE4 = {
    "Привлечение клиентов",
    "Построение команды",
    "Автоматизация процессов",
    "Обучение и развитие",
}

ALL_CHOICES = STAGE1 | STAGE2 | STAGE3 | STAGE4


async def start_callback(query: types.CallbackQuery, bot: Bot):
    buttons = reply_markup_builder(
        [
            ReplyButton(text="Уже работаю"),
            ReplyButton(text="Планирую начать"),
            ReplyButton(text="Изучаю варианты"),
        ],
        [1, 2],
    )
    await query.message.answer(
        "Вы уже стали нашим партнером или только планируете?", reply_markup=buttons
    )
    await query.answer()  # stop spinner
    await query.message.delete()


# --- single message handler for all steps ---
async def onboarding_flow(message: types.Message, bot: Bot, state: context.FSMContext):
    text = (message.text or "").strip()
    print("it is getting everything you know")
    if text in STAGE1:
        # ask experience
        buttons = reply_markup_builder(
            [
                ReplyButton(text="Нет опыта"),
                ReplyButton(text="Менее года"),
                ReplyButton(text="1-3 года"),
                ReplyButton(text="Более 3-х лет"),
            ],
            [2, 2],
        )
        await message.answer(
            "Есть ли у вас опыт в сетевом бизнесе?", reply_markup=buttons
        )
        return

    if text in STAGE2:
        # ask goals
        buttons = reply_markup_builder(
            [
                ReplyButton(text="Дополнительный доход"),
                ReplyButton(text="Развитие офлайн - бизнеса"),
                ReplyButton(text="Выход на пассив"),
                ReplyButton(text="Построение команды"),
                ReplyButton(text="Развитие личного бренда"),
                ReplyButton(text="Развитие онлайн - бизнеса"),
            ],
            [2],
        )
        await message.answer("Какие цели вы ставите перед собой?", reply_markup=buttons)
        return

    if text in STAGE3:
        # ask what's most important
        buttons = reply_markup_builder(
            [
                ReplyButton(text="Привлечение клиентов"),
                ReplyButton(text="Построение команды"),
                ReplyButton(text="Автоматизация процессов"),
                ReplyButton(text="Обучение и развитие"),
            ],
            [2],
        )
        await message.answer("Что вам сейчас важнее всего?", reply_markup=buttons)
        return

    if text in STAGE4:

        bot_client = await BotClient.objects.filter(
            chat_id=message.from_user.id
        ).afirst()
        await bot_client.aupdate_verified(True)
        # final ready screen
        return await give_parent_tree(message, bot)


start_flow_router.message.register(start, CommandStart())
start_flow_router.message.register(
    get_login_access_parameter, LoginFSM.access_parameter
)


start_flow_router.message.register(get_login_password, LoginFSM.password)
start_flow_router.callback_query.register(start_callback, F.data.startswith("start"))
start_flow_router.message.register(
    onboarding_flow,
    F.text.in_(ALL_CHOICES),
)
