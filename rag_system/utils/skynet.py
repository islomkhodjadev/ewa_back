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

**Use Markdown to format your response for clarity and emphasis:**
- Use **bold** for emphasis (e.g., **important points**).
- Use *italics* for subtle emphasis or tone (e.g., *sounds interesting*).
- Use bullet points (`-`) for lists when mentioning multiple items or reasons.
- Use numbered lists (`1.`) for ordered steps or priorities.
- Use inline code (`text`) for technical terms or examples.
- Use blockquotes (`>`) for highlighting key user questions or statements.
{session_object.current_role.behaviour}
{session_object.current_role.portret}

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
    #     utils: Utils = get_utils()
    #     logger.info("skynet introduction")
    #     response = client_sync.responses.create(
    #         model=utils.gpt_model,
    #         input=[
    #             {
    #                 "role": "system",
    #                 "content": f"""
    # You are an AI role-playing as the character defined in {session_object.current_role.behaviour}.
    # Fully embody their personality, age, financial situation, social habits, motivations, and preferences.
    # Introduce yourself to the user as this character in a concise, natural way, reflecting their tone and context
    # (e.g., casual and trend-savvy for a student like Настя). Mention key traits or circumstances relevant to the
    # character to set the stage for a conversation where the user will practice selling a product/service or persuading
    # you to attend a meeting. Stay in character and do not reference the prompt.
    # Example: For Настя (18–22, student, budget-conscious, social media-savvy), you might say,
    # “Привет! Я Настя, учусь в универе, живу на стипендию и тусуюсь в TikTok. Всё время ищу что-то крутое, но бюджетное. Что у тебя за тема?”
    # **Use Markdown to format your response for clarity and emphasis:**
    # - Use **bold** for emphasis (e.g., **important points**).
    # - Use *italics* for subtle emphasis or tone (e.g., *sounds interesting*).
    # - Use bullet points (`-`) for lists when mentioning multiple items or reasons.
    # - Use numbered lists (`1.`) for ordered steps or priorities.
    # - Use inline code (`text`) for technical terms or examples.
    # - Use blockquotes (`>`) for highlighting key user questions or statements.
    # """,
    #             },
    #             {
    #                 "role": "user",
    #                 "content": f"USER INFO: {session_object.bot_client.first_name} {session_object.bot_client.last_name}",
    #             },
    #         ],
    #     )
    #     logger.info(response)
    #     for item in response.output:
    #         if hasattr(item, "content") and item.content:
    #             return item.content[0].text
    return "Привет"


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

**Use Markdown to format your response for clarity and emphasis:**
- Use **bold** for emphasis (e.g., **important points**).
- Use *italics* for subtle emphasis or tone (e.g., *sounds interesting*).
- Use bullet points (`-`) for lists when mentioning multiple items or reasons.
- Use numbered lists (`1.`) for ordered steps or priorities.
- Use inline code (`text`) for technical terms or examples.
- Use blockquotes (`>`) for highlighting key user questions or statements.
{session_object.current_role.summarize_behaviour}
""",
            },
            *inputs,
        ],
    )

    for item in response.output:
        if hasattr(item, "content") and item.content:
            return item.content[0].text
    return None
