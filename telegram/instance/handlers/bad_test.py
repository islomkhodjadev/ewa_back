# --- handlers/bad_test.py ---
from aiogram import types, Bot, Router, F
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from telegram.instance.handlers.handle_tree_markups import give_parent_tree
from telegram.instance.middlewares import BotClientSessionMiddleWare
from telegram_client.models import BotClient
from telegram.models import (
    BadTestQuestion,
    BadTestAnswer,
    BadTestProduct,
    BadTestSession,
)

bad_test_router = Router()
bad_test_router.message.outer_middleware(BotClientSessionMiddleWare())


class BadTestStates(StatesGroup):
    waiting_for_goals = State()
    answering_questions = State()
    showing_results = State()
    waiting_for_bonus = State()
    waiting_for_recommendations = State()


@bad_test_router.message(F.text == "Подобрать БАД - тест")
async def start_bad_test(message: types.Message, state: FSMContext, client: BotClient):
    # Get existing incomplete session or create new one
    existing_session = await BadTestSession.objects.filter(client=client).afirst()

    if existing_session:
        # Reset existing session
        session = existing_session
        session.answers_data = {}
        session.is_completed = False
        session.current_question = None
        await session.asave()
    else:
        # Create new session
        session = await BadTestSession.objects.acreate(
            client=client, is_completed=False, answers_data={}
        )
    # Welcome message
    welcome_text = """
О, ты здесь! Я почти как врач, только без халата, диплома и занудства.

Если ты тут, значит:
• устал просыпаться уставшим,
• кожа говорит "пока", а нервы выходят из чата,
• волосы решили жить своей жизнью,
• а энергия заканчивается быстрее, чем батарейка на телефоне

Знакомо? Тогда ты точно по адресу!

Сейчас мы вместе пройдем короткий тест и подберем тебе БАДы, которые подходят именно тебе, а не соседке с форума.

Готов? Тогда глубоко вдохни и поехали!
    """.strip()

    # Goals selection
    goals_text = """
Выбери до 3-х целей, которые важны сейчас:
• улучшить кожу, волосы, ногти
• снятие отеков и чувства тяжести
• похудеть и убрать лишние килограммы
• улучшить концентрацию и память
• заряд энергии и бодрости
• снизить стресс и напряжение
• поддержать суставы и подвижность

Отправь номера целей через запятую (например: 1,3,5)
    """.strip()

    goals_keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="1,3,5"), KeyboardButton(text="2,4,6")],
            [KeyboardButton(text="1,2,3"), KeyboardButton(text="4,5,6")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
    )

    await message.answer(welcome_text)
    await message.answer(goals_text, reply_markup=goals_keyboard)
    await state.set_state(BadTestStates.waiting_for_goals)
    await state.update_data(session_id=session.id)


# Handle goals selection
@bad_test_router.message(
    BadTestStates.waiting_for_goals, F.text.regexp(r"^[1-7](?:,[1-7]){0,2}$")
)
async def handle_goals_selection(message: types.Message, state: FSMContext):
    goals = [int(x.strip()) for x in message.text.split(",")]

    # Map goal numbers to categories
    goal_categories = {
        1: "beauty",
        2: "edema",
        3: "weight_loss",
        4: "brain",
        5: "energy",
        6: "stress",
        7: "joints",
    }

    selected_categories = [goal_categories[goal] for goal in goals]

    # Update session
    data = await state.get_data()
    session = await BadTestSession.objects.aget(id=data["session_id"])
    session.answers_data["selected_goals"] = selected_categories
    session.answers_data["scores"] = {category: 0 for category in selected_categories}
    await session.asave()

    # Get first question
    first_question = (
        await BadTestQuestion.objects.filter(is_active=True).order_by("order").afirst()
    )
    if first_question:
        session.current_question = first_question
        await session.asave()

        answers = [
            answer async for answer in first_question.answers.all().order_by("order")
        ]
        keyboard_buttons = [
            [KeyboardButton(text=answer.answer_text)] for answer in answers
        ]
        keyboard_buttons.append([KeyboardButton(text="⬅️ Назад")])

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=keyboard_buttons)

        await message.answer(first_question.question_text, reply_markup=keyboard)
        await state.set_state(BadTestStates.answering_questions)
        await state.update_data(current_question_id=first_question.id)
    else:
        await message.answer("Извините, вопросы временно недоступны.")


# Handle question answers
@bad_test_router.message(BadTestStates.answering_questions)
async def handle_question_answer(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        # Handle back navigation
        await handle_back_in_test(message, state)
        return

    data = await state.get_data()
    session = await BadTestSession.objects.select_related("current_question").aget(
        id=data["session_id"]
    )
    current_question = session.current_question

    # Find selected answer
    answer = await BadTestAnswer.objects.filter(
        question=current_question, answer_text=message.text
    ).afirst()

    if not answer:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.")
        return

    # Update scores
    scores = session.answers_data.get("scores", {})
    for category in scores.keys():
        points_field = f"points_{category}"
        if hasattr(answer, points_field):
            scores[category] += getattr(answer, points_field, 0)

    session.answers_data["scores"] = scores
    await session.asave()

    # Get next question
    next_question = (
        await BadTestQuestion.objects.filter(
            is_active=True, order__gt=current_question.order
        )
        .order_by("order")
        .afirst()
    )

    if next_question:
        session.current_question = next_question
        await session.asave()

        answers = [
            answer async for answer in next_question.answers.all().order_by("order")
        ]
        keyboard_buttons = [
            [KeyboardButton(text=answer.answer_text)] for answer in answers
        ]
        keyboard_buttons.append([KeyboardButton(text="⬅️ Назад")])

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=keyboard_buttons)

        await message.answer(next_question.question_text, reply_markup=keyboard)
        await state.update_data(current_question_id=next_question.id)
    else:
        # Test completed
        await show_test_results(message, session, state)


async def show_test_results(
    message: types.Message, session: BadTestSession, state: FSMContext
):
    scores = session.answers_data.get("scores", {})

    # Sort categories by score
    sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_categories = [cat for cat, score in sorted_categories[:3]]

    # Get primary products - FIXED: Use list comprehension with async for
    primary_products = [
        product
        async for product in BadTestProduct.objects.filter(
            category__in=top_categories, priority="primary", is_active=True
        )
    ]

    # Get secondary products - FIXED: Use list comprehension with async for
    secondary_products = [
        product
        async for product in BadTestProduct.objects.filter(
            category__in=top_categories, priority="secondary", is_active=True
        )
    ]

    # Store results in session
    session.answers_data["primary_products"] = [p.name for p in primary_products]
    session.answers_data["secondary_products"] = [p.name for p in secondary_products]
    session.answers_data["product_details"] = {
        p.name: p.dosage for p in (primary_products + secondary_products)
    }
    session.is_completed = True
    await session.asave()

    # Show results
    primary_products_text = "\n".join(
        [f"{p.name} - {p.dosage}" for p in primary_products]
    )

    result_text = f"""
Готово! Тест пройден и вот, что мы выяснили:

Похоже твой организм шепчет:
"Эй, друг, подкинь мне немного поддержки! Тут как-то..утомительно быть человеком"

На основе твоих ответов мы собрали персональную подборку БАДов.

Твоя персональная БАД тройка:
1. {primary_products[0].name if primary_products else 'N/A'}
2. {primary_products[1].name if len(primary_products) > 1 else 'N/A'}  
3. {primary_products[2].name if len(primary_products) > 2 else 'N/A'}

Как принимать?
{primary_products_text}

Напиши "Давай!" - и я выдам тебе бонусную must have тройку "а почему я не пил(а) это раньше?"

Хочешь получить список рекомендованных БАДов с названиями, дозировками и схемой приема?
Отправь: "Хочу рекомендации" - и я все пришлю в удобном виде!

И помни: ты не ломаешься, - ты просто немного "разболтался". Починим это вместе!
    """.strip()

    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="Давай!"), KeyboardButton(text="Хочу рекомендации")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
    )

    await message.answer(result_text, reply_markup=keyboard)
    await state.set_state(BadTestStates.showing_results)


# Handle bonus request
@bad_test_router.message(BadTestStates.showing_results, F.text == "Давай!")
async def handle_bonus_request(message: types.Message, state: FSMContext):
    data = await state.get_data()
    session = await BadTestSession.objects.aget(id=data["session_id"])

    secondary_products = session.answers_data.get("secondary_products", [])
    product_details = session.answers_data.get("product_details", {})

    bonus_products_text = "\n".join(
        [
            f'{product} - {product_details.get(product, "Информация о дозировке")}'
            for product in secondary_products[:3]
        ]
    )

    bonus_text = f"""
Бонусная must have тройка:

1. {secondary_products[0] if secondary_products else 'N/A'}
2. {secondary_products[1] if len(secondary_products) > 1 else 'N/A'}
3. {secondary_products[2] if len(secondary_products) > 2 else 'N/A'}

Как принимать?
{bonus_products_text}

Отправь "Хочу рекомендации" чтобы получить полный список всех 6 продуктов!
    """.strip()

    await message.answer(bonus_text)


# Handle full recommendations request
@bad_test_router.message(BadTestStates.showing_results, F.text == "Хочу рекомендации")
async def handle_full_recommendations(message: types.Message, state: FSMContext):
    data = await state.get_data()
    session = await BadTestSession.objects.aget(id=data["session_id"])

    primary_products = session.answers_data.get("primary_products", [])
    secondary_products = session.answers_data.get("secondary_products", [])
    product_details = session.answers_data.get("product_details", {})

    primary_text = "\n".join(
        [
            f'• {product} - {product_details.get(product, "Информация о дозировке")}'
            for product in primary_products
        ]
    )

    secondary_text = "\n".join(
        [
            f'• {product} - {product_details.get(product, "Информация о дозировке")}'
            for product in secondary_products
        ]
    )

    recommendations_text = f"""
Полный список рекомендованных БАДов:

Основные продукты:
{primary_text}

Бонусные продукты:
{secondary_text}

Спасибо за прохождение теста! 🎉
    """.strip()

    await message.answer(recommendations_text)


# Handle back navigation in test
async def handle_back_in_test(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        session_id = data.get("session_id")

        if not session_id:
            # If no session ID, go directly to main menu
            await give_parent_tree(message, message.bot, from_back=True)
            await state.clear()
            return

        session = await BadTestSession.objects.select_related("current_question").aget(
            id=session_id
        )

        if session.current_question:
            # Go to previous question
            prev_question = (
                await BadTestQuestion.objects.filter(
                    is_active=True, order__lt=session.current_question.order
                )
                .order_by("-order")
                .afirst()
            )

            if prev_question:
                session.current_question = prev_question
                await session.asave()

                answers = [
                    answer
                    async for answer in prev_question.answers.all().order_by("order")
                ]
                keyboard_buttons = [
                    [KeyboardButton(text=answer.answer_text)] for answer in answers
                ]
                keyboard_buttons.append([KeyboardButton(text="⬅️ Назад")])

                keyboard = ReplyKeyboardMarkup(
                    resize_keyboard=True, keyboard=keyboard_buttons
                )

                await message.answer(prev_question.question_text, reply_markup=keyboard)
                await state.update_data(current_question_id=prev_question.id)
            else:
                # Back to goals selection - FIX: Use proper async call
                from telegram_client.models import BotClient

                client = await BotClient.objects.aget(chat_id=message.from_user.id)
                await start_bad_test(message, state, client)
        else:
            # Back to main menu
            await give_parent_tree(message, message.bot, from_back=True)
            await state.clear()

    except Exception as e:
        # If any error occurs, fallback to main menu
        logger.error(f"Error in handle_back_in_test: {e}")
        await give_parent_tree(message, message.bot, from_back=True)
        await state.clear()


import logging


logger = logging.getLogger(__name__)


@bad_test_router.message(
    F.text == "⬅️ Назад",
    StateFilter(
        BadTestStates.waiting_for_goals,
        BadTestStates.answering_questions,
        BadTestStates.showing_results,
        BadTestStates.waiting_for_bonus,
        BadTestStates.waiting_for_recommendations,
    ),
)
async def cancel_test(message: types.Message, state: FSMContext):
    logger.info("HERE FROM CANCEL TEST")
    await give_parent_tree(message, message.bot, from_back=True)
    await state.clear()
