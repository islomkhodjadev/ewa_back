# --- handlers/bad_test.py ---
from aiogram import types, Bot, Router, F
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

from telegram.instance.handlers.handle_tree_markups import give_parent_tree
from telegram.instance.middlewares import BotClientSessionMiddleWare
from telegram_client.models import BotClient
from telegram.models import (
    BadTestQuestion,
    BadTestAnswer,
    BadTestProduct,
    BadTestSession,
)

# Setup logger
logger = logging.getLogger(__name__)

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
    logger.info(
        f"Starting bad test for client {client.id} (user {message.from_user.id})"
    )

    try:
        # Get existing incomplete session or create new one
        existing_session = await BadTestSession.objects.filter(client=client).afirst()

        if existing_session:
            logger.info(f"Found existing session {existing_session.id}, resetting it")
            # Reset existing session
            session = existing_session
            session.answers_data = {}
            session.is_completed = False
            session.current_question = None
            await session.asave()
        else:
            logger.info("Creating new bad test session")
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
                [KeyboardButton(text="7,5,6"), KeyboardButton(text="1,4,7")],
                [KeyboardButton(text="⬅️ Назад")],
            ],
        )

        await message.answer(welcome_text)
        await message.answer(goals_text, reply_markup=goals_keyboard)
        await state.set_state(BadTestStates.waiting_for_goals)
        await state.update_data(session_id=session.id)

        logger.info(
            f"Bad test started successfully. Session ID: {session.id}, State: waiting_for_goals"
        )

    except Exception as e:
        logger.error(
            f"Error starting bad test for client {client.id}: {str(e)}", exc_info=True
        )
        await message.answer(
            "Произошла ошибка при запуске теста. Пожалуйста, попробуйте позже."
        )


# Handle goals selection
@bad_test_router.message(
    BadTestStates.waiting_for_goals, F.text.regexp(r"^[1-7](?:,[1-7]){0,2}$")
)
async def handle_goals_selection(message: types.Message, state: FSMContext):
    logger.info(f"Handling goals selection: {message.text}")

    try:
        goals = [int(x.strip()) for x in message.text.split(",")]
        logger.info(f"Parsed goals: {goals}")

        if len(goals) > 3:
            logger.warning(f"User selected too many goals: {len(goals)}")
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
        logger.info(f"Selected categories: {selected_categories}")

        # Update session
        data = await state.get_data()
        session_id = data.get("session_id")
        if not session_id:
            logger.error("No session_id found in state data")
            await message.answer("Ошибка сессии. Пожалуйста, начните тест заново.")
            return

        session = await BadTestSession.objects.aget(id=session_id)
        session.answers_data["selected_goals"] = selected_categories
        session.answers_data["scores"] = {
            category: 0 for category in selected_categories
        }
        await session.asave()
        logger.info(f"Updated session {session.id} with goals and initial scores")

        # Get first question (should be 7 questions total)
        first_question = (
            await BadTestQuestion.objects.filter(is_active=True)
            .order_by("order")
            .afirst()
        )

        if first_question:
            logger.info(
                f"Found first question: {first_question.id} (order: {first_question.order})"
            )
            session.current_question = first_question
            await session.asave()

            answers = [
                answer
                async for answer in first_question.answers.all().order_by("order")
            ]
            logger.info(
                f"Found {len(answers)} answers for question {first_question.id}"
            )

            keyboard_buttons = [
                [KeyboardButton(text=answer.answer_text)] for answer in answers
            ]
            keyboard_buttons.append([KeyboardButton(text="⬅️ Назад")])

            keyboard = ReplyKeyboardMarkup(
                resize_keyboard=True, keyboard=keyboard_buttons
            )

            await message.answer(first_question.question_text, reply_markup=keyboard)
            await state.set_state(BadTestStates.answering_questions)
            await state.update_data(current_question_id=first_question.id)

            logger.info(
                f"Transitioned to answering_questions state. Current question: {first_question.id}"
            )
        else:
            logger.warning("No active questions found in database")
            await message.answer("Извините, вопросы временно недоступны.")

    except Exception as e:
        logger.error(f"Error handling goals selection: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка при обработке выбора целей. Пожалуйста, попробуйте позже."
        )


# Handle question answers (7 questions)
@bad_test_router.message(BadTestStates.answering_questions)
async def handle_question_answer(message: types.Message, state: FSMContext):
    logger.info(f"Handling question answer: {message.text}")

    if message.text == "⬅️ Назад":
        logger.info("Back button pressed in answering_questions state")
        await handle_back_in_test(message, state)
        return

    try:
        data = await state.get_data()
        session_id = data.get("session_id")
        if not session_id:
            logger.error("No session_id found in state data")
            await message.answer("Ошибка сессии. Пожалуйста, начните тест заново.")
            return

        session = await BadTestSession.objects.select_related("current_question").aget(
            id=session_id
        )
        current_question = session.current_question

        if not current_question:
            logger.error("No current question found in session")
            await message.answer(
                "Ошибка: вопрос не найден. Пожалуйста, начните тест заново."
            )
            return

        logger.info(
            f"Processing answer for question {current_question.id} (order: {current_question.order})"
        )

        # Find selected answer
        answer = await BadTestAnswer.objects.filter(
            question=current_question, answer_text=message.text
        ).afirst()

        if not answer:
            logger.warning(
                f"Invalid answer selected: '{message.text}' for question {current_question.id}"
            )
            await message.answer("Пожалуйста, выбери один из предложенных вариантов.")
            return

        logger.info(f"Found answer: {answer.id} for question {current_question.id}")

        # Update scores based on answer points
        scores = session.answers_data.get("scores", {})
        points_added = {}

        for category in scores.keys():
            points_field = f"points_{category}"
            if hasattr(answer, points_field):
                points_value = getattr(answer, points_field, 0)
                scores[category] += points_value
                points_added[category] = points_value

        session.answers_data["scores"] = scores
        await session.asave()
        logger.info(f"Updated scores: {scores}. Points added: {points_added}")

        # Get next question (7 questions total)
        next_question = (
            await BadTestQuestion.objects.filter(
                is_active=True, order__gt=current_question.order
            )
            .order_by("order")
            .afirst()
        )

        if next_question:
            logger.info(
                f"Moving to next question: {next_question.id} (order: {next_question.order})"
            )
            session.current_question = next_question
            await session.asave()

            answers = [
                answer async for answer in next_question.answers.all().order_by("order")
            ]
            logger.info(f"Found {len(answers)} answers for next question")

            keyboard_buttons = [
                [KeyboardButton(text=answer.answer_text)] for answer in answers
            ]
            keyboard_buttons.append([KeyboardButton(text="⬅️ Назад")])

            keyboard = ReplyKeyboardMarkup(
                resize_keyboard=True, keyboard=keyboard_buttons
            )

            await message.answer(next_question.question_text, reply_markup=keyboard)
            await state.update_data(current_question_id=next_question.id)
        else:
            # All 7 questions completed - show results
            logger.info("All questions completed, showing results")
            await show_test_results(message, session, state)

    except Exception as e:
        logger.error(f"Error handling question answer: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка при обработке ответа. Пожалуйста, попробуйте позже."
        )


async def show_test_results(
    message: types.Message, session: BadTestSession, state: FSMContext
):
    logger.info(f"Showing test results for session {session.id}")

    try:
        scores = session.answers_data.get("scores", {})
        logger.info(f"Final scores: {scores}")

        # Sort categories by score (highest first)
        sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        logger.info(f"Sorted categories by score: {sorted_categories}")

        # Get top categories (up to 3 based on user's goal selection)
        top_categories = [cat for cat, score in sorted_categories]
        logger.info(f"Top categories: {top_categories}")

        # Get products for the selected categories
        all_products = [
            product
            async for product in BadTestProduct.objects.filter(
                category__in=top_categories, is_active=True
            )
        ]
        logger.info(
            f"Found {len(all_products)} total products for categories {top_categories}"
        )

        # Sort products by priority (primary first) and then by score
        def product_sort_key(product):
            category_score = scores.get(product.category, 0)
            priority_score = 2 if product.priority == "primary" else 1
            return (category_score, priority_score)

        sorted_products = sorted(all_products, key=product_sort_key, reverse=True)
        logger.info(f"Sorted {len(sorted_products)} products by priority and score")

        # Take available products (up to 6 total)
        selected_products = sorted_products[:6]
        logger.info(f"Selected {len(selected_products)} products for recommendation")

        # Split into primary (first 3) and bonus (next 3)
        primary_products = selected_products[:3]
        bonus_products = selected_products[3:6] if len(selected_products) > 3 else []

        logger.info(
            f"Primary products: {len(primary_products)}, Bonus products: {len(bonus_products)}"
        )
        logger.info(f"Primary product names: {[p.name for p in primary_products]}")
        if bonus_products:
            logger.info(f"Bonus product names: {[p.name for p in bonus_products]}")

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
        logger.info(f"Session {session.id} marked as completed with results")

        # Build result text dynamically based on available products
        if len(primary_products) >= 3:
            logger.info("Showing full 3-product results")
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
        elif len(primary_products) > 0:
            # Handle case with fewer than 3 products
            logger.info(
                f"Showing results with {len(primary_products)} primary products"
            )
            product_list = "\n".join(
                [f"{i+1}. {p.name}" for i, p in enumerate(primary_products)]
            )
            primary_products_text = "\n".join(
                [f"• {p.name} - {p.dosage}" for p in primary_products]
            )

            result_text = f"""
Готово! Тест пройден и вот, что мы выяснили:

На основе твоих ответов мы собрали персональную подборку БАДов.

Твоя персональная БАД подборка:
{product_list}

Как принимать?
{primary_products_text}

На основе твоих ответов мы подобрали {len(primary_products)} основных продукт(а/ов).
            """.strip()
        else:
            # No products found
            logger.warning("No products found for the selected categories")
            result_text = """
Готово! Тест пройден.

К сожалению, по результатам теста мы не смогли подобрать подходящие БАДы для выбранных целей.

Попробуйте выбрать другие цели или обратитесь к консультанту для индивидуальной консультации.
            """.strip()

        keyboard_buttons = []
        if bonus_products:
            logger.info("Adding bonus products buttons")
            keyboard_buttons.append(
                [
                    KeyboardButton(text="Давай!"),
                    KeyboardButton(text="Хочу рекомендации"),
                ]
            )
        elif primary_products:
            logger.info("Adding recommendations button only (no bonus products)")
            keyboard_buttons.append([KeyboardButton(text="Хочу рекомендации")])

        keyboard_buttons.append([KeyboardButton(text="⬅️ Назад")])

        keyboard = ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=keyboard_buttons,
        )

        await message.answer(result_text, reply_markup=keyboard)
        await state.set_state(BadTestStates.showing_results)
        logger.info(
            "Successfully showed test results and transitioned to showing_results state"
        )

    except Exception as e:
        logger.error(f"Error showing test results: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка при показе результатов. Пожалуйста, попробуйте позже."
        )


# Handle bonus request - show second trio
@bad_test_router.message(BadTestStates.showing_results, F.text == "Давай!")
async def handle_bonus_request(message: types.Message, state: FSMContext):
    logger.info("Handling bonus request")

    try:
        data = await state.get_data()
        session_id = data.get("session_id")
        if not session_id:
            logger.error("No session_id found in state data")
            await message.answer("Ошибка сессии. Пожалуйста, начните тест заново.")
            return

        session = await BadTestSession.objects.aget(id=session_id)
        bonus_products = session.answers_data.get("bonus_products", [])
        product_details = session.answers_data.get("product_details", {})

        logger.info(f"Bonus products requested: {len(bonus_products)} products")

        if not bonus_products:
            logger.warning("No bonus products available")
            await message.answer("Бонусные продукты недоступны.")
            return

        bonus_products_text = "\n".join(
            [
                f"• {product} - {product_details[product]['dosage']}"
                for product in bonus_products
            ]
        )

        bonus_list = "\n".join(
            [f"{i+1}. {product}" for i, product in enumerate(bonus_products)]
        )

        bonus_text = f"""
Бонусная must have подборка "а почему я не пил(а) это раньше?":

{bonus_list}

Как принимать?
{bonus_products_text}

Спасибо за прохождение теста! 🎉
Надеемся, эти рекомендации помогут тебе чувствовать себя лучше!
        """.strip()

        await message.answer(bonus_text)
        logger.info("Successfully showed bonus products")
        await give_parent_tree(message, message.bot, from_back=True)
        await state.clear()
        logger.info("Bonus request completed, state cleared")

    except Exception as e:
        logger.error(f"Error handling bonus request: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка при показе бонусных продуктов. Пожалуйста, попробуйте позже."
        )


# Handle full recommendations request - show all 6 products
@bad_test_router.message(BadTestStates.showing_results, F.text == "Хочу рекомендации")
async def handle_full_recommendations(message: types.Message, state: FSMContext):
    logger.info("Handling full recommendations request")

    try:
        data = await state.get_data()
        session_id = data.get("session_id")
        if not session_id:
            logger.error("No session_id found in state data")
            await message.answer("Ошибка сессии. Пожалуйста, начните тест заново.")
            return

        session = await BadTestSession.objects.aget(id=session_id)
        primary_products = session.answers_data.get("primary_products", [])
        bonus_products = session.answers_data.get("bonus_products", [])
        product_details = session.answers_data.get("product_details", {})

        logger.info(
            f"Full recommendations requested. Primary: {len(primary_products)}, Bonus: {len(bonus_products)}"
        )

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
Полный список рекомендованных БАДов ({len(primary_products) + len(bonus_products)} продуктов):

🎯 Основные продукты:
{primary_text}

🎁 Бонусные продукты:
{bonus_text}

Спасибо за прохождение теста! 🎉
Надеемся, эти рекомендации помогут тебе чувствовать себя лучше!
        """.strip()

        await message.answer(recommendations_text)
        logger.info("Successfully showed full recommendations")
        # For other states, go to main menu
        await give_parent_tree(message, message.bot, from_back=True)
        await state.clear()
        logger.info("Full recommendations completed, state cleared")

    except Exception as e:
        logger.error(f"Error handling full recommendations: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка при показе рекомендаций. Пожалуйста, попробуйте позже."
        )


# Handle back navigation
async def handle_back_in_test(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    logger.info(f"Handling back navigation from state: {current_state}")

    try:
        if current_state == BadTestStates.waiting_for_goals:
            logger.info("Back from waiting_for_goals - returning to main menu")
            # Go back to main menu
            await give_parent_tree(message, message.bot, from_back=True)
            await state.clear()
        elif current_state == BadTestStates.answering_questions:
            logger.info(
                "Back from answering_questions - going to previous question or goals"
            )
            data = await state.get_data()
            session_id = data.get("session_id")
            if not session_id:
                logger.error("No session_id found in state data")
                await message.answer("Ошибка сессии. Пожалуйста, начните тест заново.")
                return

            session = await BadTestSession.objects.select_related(
                "current_question"
            ).aget(id=session_id)

            # Go to previous question or back to goals
            prev_question = (
                await BadTestQuestion.objects.filter(
                    is_active=True, order__lt=session.current_question.order
                )
                .order_by("-order")
                .afirst()
            )

            if prev_question:
                logger.info(
                    f"Going back to previous question: {prev_question.id} (order: {prev_question.order})"
                )
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
            else:
                logger.info("No previous question found - returning to goals selection")
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
                        [KeyboardButton(text="7,5,6"), KeyboardButton(text="1,4,7")],
                        [KeyboardButton(text="⬅️ Назад")],
                    ],
                )
                await message.answer(goals_text, reply_markup=goals_keyboard)
                await state.set_state(BadTestStates.waiting_for_goals)
        else:
            logger.info(f"Back from {current_state} - returning to main menu")
            # For other states, go to main menu
            await give_parent_tree(message, message.bot, from_back=True)
            await state.clear()

    except Exception as e:
        logger.error(f"Error handling back navigation: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка при навигации. Пожалуйста, попробуйте позже."
        )


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
    logger.info(f"Back button pressed by user {message.from_user.id}")
    await handle_back_in_test(message, state)
