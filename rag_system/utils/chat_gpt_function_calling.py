from django.conf import settings
import json
from openai import AsyncOpenAI, OpenAI
from rag_system.models import Embedding
from .gpt_rules import get_utils, get_utils_async

from typing import Optional, Dict
from rag_system.models import Utils
from miniapp.models import ChatSession

client_async = AsyncOpenAI(api_key=settings.GPT_TOKEN)
client_sync = OpenAI(api_key=settings.GPT_TOKEN)

tools = [
    {
        "type": "function",
        "name": "provide_id_and_answer",
        "description": "Provide answer and ID of the source content if used, otherwise use -1",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "ID of the source content used for the answer. Use -1 if no specific content was used.",
                },
                "answer": {
                    "type": "string",
                    "description": "Text answer for the user's request",
                },
            },
            "required": ["id", "answer"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


async def get_answer_gpt_function_async(
    user_prompt: str, contents: Embedding, session_object: ChatSession
) -> Optional[Dict]:
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
                {utils.choose_embedding_rule}
                
                AVAILABLE CONTENT WITH IDs:
                {' | '.join(f'id: {embedding.id}; content: {embedding.raw_text}' for embedding in contents)}
                HERE ENDS CONTENT WITH IDs.
                
                
                
                """,
            },
            *inputs,
        ],
        tools=tools,
        tool_choice={"type": "function", "name": "provide_id_and_answer"},
    )
    for item in response.output:
        if hasattr(item, "arguments"):
            print(item.arguments)
            return item.arguments

    return None


def get_answer_gpt_function(
    user_prompt: str, contents: Embedding, session_object: ChatSession
) -> Optional[Dict]:
    utils: Utils = get_utils()
    inputs = session_object.get_history(utils.last_message_count)
    response = client_sync.responses.create(
        model=utils.gpt_model,
        input=[
            {
                "role": "system",
                "content": f"""
                {utils.base_rules}
                {utils.base_information}
                {utils.choose_embedding_rule}
                
                AVAILABLE CONTENT WITH IDs:
                {' | '.join(f'id: {embedding.id}; content: {embedding.raw_text}' for embedding in contents)}
                HERE ENDS CONTENT WITH IDs.
                
                
                
                """,
            },
            *inputs,
        ],
        tools=tools,
        tool_choice={"type": "function", "name": "provide_id_and_answer"},
    )
    for item in response.output:
        if hasattr(item, "arguments"):
            return item.arguments
    return None
