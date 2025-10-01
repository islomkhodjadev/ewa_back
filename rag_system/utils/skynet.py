from django.conf import settings
import json
from openai import AsyncOpenAI, OpenAI
from rag_system.models import Embedding, Roles
from .gpt_rules import get_utils, get_utils_async

from typing import Optional, Dict
from rag_system.models import Utils
from miniapp.models import ChatSession
import logging

logger = logging.getLogger(__name__)

client_async = AsyncOpenAI(api_key=settings.GPT_TOKEN)
client_sync = OpenAI(api_key=settings.GPT_TOKEN)


async def skynet_answer_async(user_prompt: str, session_object: ChatSession) -> str:
    utils: Utils = await get_utils_async()
    inputs = await session_object.get_history_async(utils.last_message_count)
    response = await client_async.responses.create(
        model=utils.gpt_model,
        input=[
            {
                "role": "system",
                "content": f"""
                {utils.base_rules}
                {utils.base_information}
                {session_object.current_role.behaviour}
                """,
            },
            *inputs,
        ],
    )
    for item in response.output:
        if hasattr(item, "content") and item.content:
            return item.content[0].text
    return None


def skynet_answer(user_prompt: str, session_object: ChatSession) -> str:

    logger.info("skynet simple answers")
    utils: Utils = get_utils()
    inputs = session_object.get_last_summarization_history_v2()
    response = client_sync.responses.create(
        model=utils.gpt_model,
        input=[
            {
                "role": "system",
                "content": f"""
You are an AI role-playing as the character defined in {session_object.current_role.behaviour}. 
Embody their personality, motivations, habits, pain points, and decision-making style.
Engage in a conversation with a user practicing their skills in selling a product/service or persuading you to attend a meeting.
Respond realistically, reflecting the character’s age, 
financial situation, social habits, and preferences. 
Use conversational language matching their tone (e.g., casual, trend-conscious for Настя). Evaluate sales pitches for affordability, relevance, 
and social proof, asking about price, benefits, or reviews. For meeting invitations, respond based on the character’s
schedule, trust, and interest. Stay in character, consistent with {session_object.current_role.behaviour}, 
without referencing the prompt.
Example: For Настя, you might say, “О, звучит прикольно, но дорого? Есть отзывы в TikTok?” or “Круто, но я занята учебой, когда встреча?”
""",
            },
            *inputs,
        ],
    )
    for item in response.output:
        if hasattr(item, "content") and item.content:
            return item.content[0].text
    return None


def skynet_introduce(session_object: ChatSession) -> str:
    utils: Utils = get_utils()
    logger.info("skynet introduction")
    response = client_sync.responses.create(
        model=utils.gpt_model,
        input=[
            {
                "role": "system",
                "content": f"""
You are an AI role-playing as the character defined in {session_object.current_role.behaviour}. 
Fully embody their personality, age, financial situation, social habits, motivations, and preferences. 
Introduce yourself to the user as this character in a concise, natural way, reflecting their tone and context 
(e.g., casual and trend-savvy for a student like Настя). Mention key traits or circumstances relevant to the 
character to set the stage for a conversation where the user will practice selling a product/service or persuading 
you to attend a meeting. Stay in character and do not reference the prompt.
Example: For Настя (18–22, student, budget-conscious, social media-savvy), you might say,
“Привет! Я Настя, учусь в универе, живу на стипендию и тусуюсь в TikTok. Всё время ищу что-то крутое, но бюджетное. Что у тебя за тема?”
""",
            },
            {
                "role": "user",
                "content": f"USER INFO: {session_object.bot_client.first_name} {session_object.bot_client.last_name}",
            },
        ],
    )
    logger.info(response)
    for item in response.output:
        if hasattr(item, "content") and item.content:
            return item.content[0].text
    return None


def skynet_summarize(session_object: ChatSession) -> str:
    utils: Utils = get_utils()
    inputs = session_object.get_last_summarization_history_v2()
    logger.info(inputs)

    response = client_sync.responses.create(
        model=utils.gpt_model,
        input=[
            {
                "role": "system",
                "content": f"""
                {utils.base_rules}
                {utils.base_information}
                """,
            },
            *inputs,
            {
                "role": "user",
                "content": f"""
Based on the conversation history, provide a concise summary
and feedback focusing solely on the user’s behavior, not your own responses. 
You are role-playing as the character defined in {session_object.current_role.behaviour}.
Analyze the user’s communication style, questions, interests, and needs. 
Provide actionable feedback on how the user could improve their approach to better persuade or sell to this character,
considering their motivations, pain points, and preferences (e.g., for Настя: emphasize affordability, social proof, or trendy appeals). 
Stay in character’s context without referencing the prompt.
Example: For Настя, you might say, 
“You sounded enthusiastic, but I got lost without clear pricing. Next time, mention student discounts or TikTok reviews early—I’d be more hooked!”
""",
            },
        ],
    )
    for item in response.output:
        if hasattr(item, "content") and item.content:
            return item.content[0].text
    return None
