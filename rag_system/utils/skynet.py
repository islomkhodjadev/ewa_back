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
    inputs = session_object.get_history(utils.last_message_count)
    response = client_sync.responses.create(
        model=utils.gpt_model,
        input=[
            {
                "role": "system",
                "content": f"""
                This is base rules:
                {utils.base_rules}
                this is company information
                {utils.base_information}
                Now this:
                 YOU ARE NOW THIS PERSON THIS IS YOUR DESCRIPTION:
                 MAKE CONVERSATION LIKE PErson with few words, sentence.
                 your user person is:
                {session_object.current_role.behaviour}.
                
                MAKE CONVERSATION LIKE THIS PERSON. THINK YOURSELF AS THIS PERSON.
                answer for the user request like person no need for big answers small concise answers only.
                Analyze the history of the chat and react properly
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
                {utils.base_rules}
                {utils.base_information}
                YOU ARE NOW THIS PERSON THIS IS YOUR DESCRIPTION:
                {session_object.current_role.behaviour}
                BASED ON THIS INTRODUCE YOURSELF TO THE USER FULLY DESCRIBE YOURSELF AS A PERSON ABOVE NOW YOU ARE THAT PERSON ANSWER LIKE THIS PERSON
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
                "content": f"""Based on the conversation history above, provide a comprehensive summary and feedback.

                FOCUS ON ANALYZING THE USER'S BEHAVIOR, not your own responses.
                
                {session_object.current_role.summarize_behaviour}
                
                IMPORTANT: Your summary should focus on:
                - The user's communication style and patterns
                - The user's questions and interests
                - The user's needs and preferences
                - Feedback for the USER's approach
                
                - Do not analyze or summarize your own responses
                """,
            },
        ],
    )
    for item in response.output:
        if hasattr(item, "content") and item.content:
            return item.content[0].text
    return None
