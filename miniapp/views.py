from rest_framework import views, viewsets, mixins, generics, permissions, decorators
from django.shortcuts import get_object_or_404
from telegram_client.models import BotClient
from telegram_client.serializers import BotClientSerializers
from miniapp.models import ChatSession
from miniapp.serializers import ChatSessionSerializer
from django.core.exceptions import ObjectDoesNotExist


class BotClientViewset(
    viewsets.GenericViewSet,
):
    queryset = BotClient.objects.all()
    serializer_class = BotClientSerializers

    @decorators.action(methods=["GET"], detail=False, url_path="me")
    def me(self, request, *args, **kwargs):
        chat_id = request.data.get("chat_id", None)
        if chat_id is None:
            return views.Response(
                {"error": "chat id is required"},
                status=views.status.HTTP_400_BAD_REQUEST,
            )

        bot_client = get_object_or_404(BotClient, chat_id=chat_id)

        serialized_data = self.serializer_class(instance=bot_client)
        return views.Response(serialized_data.data)

    @decorators.action(methods=["GET"], detail=False, url_path="chatsession")
    def chatsession(self, request, *args, **kwargs):
        chat_id = request.data.get("chat_id", None)
        if chat_id is None:
            return views.Response(
                {"error": "chat id is required"},
                status=views.status.HTTP_400_BAD_REQUEST,
            )

        bot_client = get_object_or_404(BotClient, chat_id=chat_id)

        try:
            session = bot_client.chatsession  # may raise RelatedObjectDoesNotExist
        except ObjectDoesNotExist:
            return views.Response(
                {"error": "chat session has not started yet"},
                status=views.status.HTTP_400_BAD_REQUEST,
            )
        serialized_data = ChatSessionSerializer(instance=session)

        return views.Response(data=serialized_data.data)
