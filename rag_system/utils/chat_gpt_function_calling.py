from django.conf import settings
import json
from openai import AsyncOpenAI, OpenAI
from rag_system.models import Embedding
from rag_system.utils import gpt_rules
from typing import Optional, Dict

client_async = AsyncOpenAI(api_key=settings.GPT_TOKEN)
client_sync = OpenAI(api_key=settings.GPT_TOKEN)

tools = [
    {
        "type": "function",
        "name": "provide_id_and_answer",
        "description": "Get id for exact information from which i give files",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "id of the  file which i should retrieve files or media files to give user",
                },
                "answer": {
                    "type": "string",
                    "description": "text format of the answer for the request from the sources given",
                },
            },
            "required": ["id", "answer"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


async def get_answer_gpt_function_async(
    user_prompt: str, contents: Embedding
) -> Optional[Dict]:

    response = await client_async.responses.create(
        model="gpt-4.1-nano",
        input=[
            {
                "role": "system",
                "content": f"""
                {gpt_rules}
                you are "EWA Assistant AI" by EWA PRODUCT
                here you should give the id and answer from these contents for user request
                {', '.join(f'id: {embedding.id}; content: {embedding.raw_text}' for embedding in contents)}""",
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        tools=tools,
        tool_choice={"type": "function", "name": "provide_id_and_answer"},
    )
    for item in response.output:
        if hasattr(item, "arguments"):
            return item.arguments
    return None


def get_answer_gpt_function(user_prompt: str, contents: Embedding) -> Optional[Dict]:

    response = client_sync.responses.create(
        model="gpt-4.1-nano",
        input=[
            {
                "role": "system",
                "content": f"""
                {gpt_rules}
                you are "EWA Assistant AI" by EWA PRODUCT
                here you should give the id and answer from these contents for user request
                {', '.join(f'id: {embedding.id}; content: {embedding.raw_text}' for embedding in contents)}""",
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        tools=tools,
        tool_choice={"type": "function", "name": "provide_id_and_answer"},
    )

    for item in response.output:
        if hasattr(item, "arguments"):
            return item.arguments
    return None
