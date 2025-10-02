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

    # Welcome message (exactly as specified)
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

    # Goals selection (up to 3 goals)
    goals_text = """
Выбери до 3-х целей, которые важны сейчас:
1. улучшить кожу, волосы, ногти
2. снятие отеков и чувства тяжести  
3. похудеть и убрать лишние килограммы
4. улучшить концентрацию и память
5. заряд энергии и бодрости
6. снизить стресс и напряжение
7. поддержать суставы и подвижность

Отправь номера целей через запятую (например: 1,3,5)
    """.strip()

    goals_keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="1,3,5"), KeyboardButton(text="2,4,6")],
            [KeyboardButton(text="1,2,3"), KeyboardButton(text="4,5,6")],
            [KeyboardButton(text="7"), KeyboardButton(text="1,4,7")],
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

    if len(goals) > 3:
        await message.answer("Пожалуйста, выбери не более 3-х целей.")
        return

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

    # Get first question (should be 7 questions total)
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


# Handle question answers (7 questions)
@bad_test_router.message(BadTestStates.answering_questions)
async def handle_question_answer(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
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
        await message.answer("Пожалуйста, выбери один из предложенных вариантов.")
        return

    # Update scores based on answer points
    scores = session.answers_data.get("scores", {})
    for category in scores.keys():
        points_field = f"points_{category}"
        if hasattr(answer, points_field):
            scores[category] += getattr(answer, points_field, 0)

    session.answers_data["scores"] = scores
    await session.asave()

    # Get next question (7 questions total)
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
        # All 7 questions completed - show results
        await show_test_results(message, session, state)


async def show_test_results(
    message: types.Message, session: BadTestSession, state: FSMContext
):
    scores = session.answers_data.get("scores", {})

    # Sort categories by score (highest first)
    sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Get top categories (up to 3 based on user's goal selection)
    top_categories = [cat for cat, score in sorted_categories]

    # Get products for the selected categories
    all_products = [
        product
        async for product in BadTestProduct.objects.filter(
            category__in=top_categories, is_active=True
        )
    ]

    # Sort products by priority (primary first) and then by score
    def product_sort_key(product):
        category_score = scores.get(product.category, 0)
        priority_score = 2 if product.priority == "primary" else 1
        return (category_score, priority_score)

    sorted_products = sorted(all_products, key=product_sort_key, reverse=True)

    # Take first 6 products (3 primary + 3 bonus)
    selected_products = sorted_products[:6]

    # Split into primary (first 3) and bonus (next 3)
    primary_products = selected_products[:3]
    bonus_products = selected_products[3:6]

    # Store results in session
    session.answers_data["primary_products"] = [p.name for p in primary_products]
    session.answers_data["bonus_products"] = [p.name for p in bonus_products]
    session.answers_data["all_products"] = [p.name for p in selected_products]
    session.answers_data["product_details"] = {
        p.name: {
            "dosage": p.dosage,
            "description": p.description,
            "category": p.category,
        }
        for p in selected_products
    }
    session.is_completed = True
    await session.asave()

    # Show results with exactly 3 primary products
    primary_products_text = "\n".join(
        [f"• {p.name} - {p.dosage}" for p in primary_products]
    )

    result_text = f"""
Готово! Тест пройден и вот, что мы выяснили:

На основе твоих ответов мы собрали персональную подборку БАДов.

Твоя персональная БАД тройка:
1. {primary_products[0].name}
2. {primary_products[1].name}  
3. {primary_products[2].name}

Как принимать?
{primary_products_text}

Напиши "Давай!" - и я выдам тебе бонусную must have тройку "а почему я не пил(а) это раньше?"

Хочешь получить список рекомендованных БАДов с названиями, дозировками и схемой приема?
Отправь: "Хочу рекомендации" - и я все пришлю в удобном виде!
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


# Handle bonus request - show second trio
@bad_test_router.message(BadTestStates.showing_results, F.text == "Давай!")
async def handle_bonus_request(message: types.Message, state: FSMContext):
    data = await state.get_data()
    session = await BadTestSession.objects.aget(id=data["session_id"])

    bonus_products = session.answers_data.get("bonus_products", [])
    product_details = session.answers_data.get("product_details", {})

    bonus_products_text = "\n".join(
        [
            f"• {product} - {product_details[product]['dosage']}"
            for product in bonus_products
        ]
    )

    bonus_text = f"""
Бонусная must have тройка "а почему я не пил(а) это раньше?":

1. {bonus_products[0]}
2. {bonus_products[1]}
3. {bonus_products[2]}

Как принимать?
{bonus_products_text}

Отправь "Хочу рекомендации" чтобы получить полный список всех 6 продуктов!
    """.strip()

    await message.answer(bonus_text)


# Handle full recommendations request - show all 6 products
@bad_test_router.message(BadTestStates.showing_results, F.text == "Хочу рекомендации")
async def handle_full_recommendations(message: types.Message, state: FSMContext):
    data = await state.get_data()
    session = await BadTestSession.objects.aget(id=data["session_id"])

    primary_products = session.answers_data.get("primary_products", [])
    bonus_products = session.answers_data.get("bonus_products", [])
    product_details = session.answers_data.get("product_details", {})

    primary_text = "\n".join(
        [
            f"• {product} - {product_details[product]['dosage']}"
            for product in primary_products
        ]
    )

    bonus_text = "\n".join(
        [
            f"• {product} - {product_details[product]['dosage']}"
            for product in bonus_products
        ]
    )

    recommendations_text = f"""
Полный список рекомендованных БАДов (6 продуктов):

🎯 Основные продукты:
{primary_text}

🎁 Бонусные продукты:
{bonus_text}

Спасибо за прохождение теста! 🎉
Надеемся, эти рекомендации помогут тебе чувствовать себя лучше!
    """.strip()

    await message.answer(recommendations_text)


# Handle back navigation
async def handle_back_in_test(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == BadTestStates.waiting_for_goals:
        # Go back to main menu
        await give_parent_tree(message, message.bot, from_back=True)
        await state.clear()
    elif current_state == BadTestStates.answering_questions:
        data = await state.get_data()
        session = await BadTestSession.objects.select_related("current_question").aget(
            id=data["session_id"]
        )

        # Go to previous question or back to goals
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
                answer async for answer in prev_question.answers.all().order_by("order")
            ]
            keyboard_buttons = [
                [KeyboardButton(text=answer.answer_text)] for answer in answers
            ]
            keyboard_buttons.append([KeyboardButton(text="⬅️ Назад")])

            keyboard = ReplyKeyboardMarkup(
                resize_keyboard=True, keyboard=keyboard_buttons
            )
            await message.answer(prev_question.question_text, reply_markup=keyboard)
        else:
            # Back to goals selection
            goals_text = """
Выбери до 3-х целей, которые важны сейчас:
1. улучшить кожу, волосы, ногти
2. снятие отеков и чувства тяжести  
3. похудеть и убрать лишние килограммы
4. улучшить концентрацию и память
5. заряд энергии и бодрости
6. снизить стресс и напряжение
7. поддержать суставы и подвижность

Отправь номера целей через запятую (например: 1,3,5)
            """.strip()

            goals_keyboard = ReplyKeyboardMarkup(
                resize_keyboard=True,
                keyboard=[
                    [KeyboardButton(text="1,3,5"), KeyboardButton(text="2,4,6")],
                    [KeyboardButton(text="1,2,3"), KeyboardButton(text="4,5,6")],
                    [KeyboardButton(text="7"), KeyboardButton(text="1,4,7")],
                    [KeyboardButton(text="⬅️ Назад")],
                ],
            )
            await message.answer(goals_text, reply_markup=goals_keyboard)
            await state.set_state(BadTestStates.waiting_for_goals)
    else:
        # For other states, go to main menu
        await give_parent_tree(message, message.bot, from_back=True)
        await state.clear()


# Back button handler for all states
@bad_test_router.message(
    F.text == "⬅️ Назад",
    StateFilter(
        BadTestStates.waiting_for_goals,
        BadTestStates.answering_questions,
        BadTestStates.showing_results,
    ),
)
async def cancel_test(message: types.Message, state: FSMContext):
    await handle_back_in_test(message, state)
