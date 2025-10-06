import httpx
import asyncio
from telegram_client.models import BotClient, BotClientSession


async def login_post(access_parameter: str, password: str):
    async with httpx.AsyncClient() as session:
        response = await session.post(
            "https://dev.ewaproduct.com/api/auth",
            json={"access_parameter": access_parameter, "password": password},
        )
        return response.status_code, response.json()


async def fill_and_activate_user(data, chat_id):
    phone_number = data["client_partner"]["main_user_data"]["phone"]
    first_name = data["client_partner"]["main_user_data"]["name"]
    last_name = data["client_partner"]["main_user_data"]["surname"]
    id = data["client_partner"]["main_user_data"]["id"]
    bot_client = await BotClient.objects.filter(chat_id=chat_id).afirst()
    await bot_client.aupdate_fields(
        is_logined=True,
        phone_number=phone_number,
        first_name=first_name,
        last_name=last_name,
        client_id=id,
    )
    session = await BotClientSession.objects.filter(client=bot_client).afirst()
    if session:
        session.current_button = None
        await session.asave(update_fields=["current_button"])

    return first_name, last_name
