from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from rest_framework.views import Response, status, APIView

from django.conf import settings
from telegram.feed_passer import BotFeedPasser
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
async def webhook_async_view(request, bot_id: str):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    if not bot_id:
        return JsonResponse(
            {"detail": "Bot ID is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    if bot_id != settings.BOT_TOKEN.split(":", maxsplit=1)[0]:
        return JsonResponse({"detail": "Bot id is not valid"})

    update = request.body.decode("utf-8")

    try:
        update_data = json.loads(update)
        await BotFeedPasser.feed_pass(token=settings.BOT_TOKEN, update=update_data)

        return JsonResponse({"status": "ok"})

    except Exception as exc:
        logger.error("Error webhook WebhookApiView: %s", exc)
        return JsonResponse(
            {"status": "error", "error": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
