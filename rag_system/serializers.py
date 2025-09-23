# serializers.py
from rest_framework import serializers
from rag_system.models import Embedding, EmbeddingData, Roles
from django.conf import settings


class EmbeddingDataSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = EmbeddingData
        # no need to echo the FK back; the parent serializer carries it
        fields = ("id", "file", "file_url")
        read_only_fields = ("id",)

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        url = obj.file.url
        if request:
            return request.build_absolute_uri(url)
        # fallback: settings must have SITE_URL or MEDIA_URL
        return f"{settings.BOT_HOST}{url}"


class EmbeddingSerializer(serializers.ModelSerializer):
    data = EmbeddingDataSerializer(many=True, read_only=True)

    class Meta:
        model = Embedding
        # include embedded_vector if you want to ship the vector too:
        # fields = ("id", "raw_text", "embedded_vector", "data")
        fields = ("id", "raw_text", "data")
        read_only_fields = ("id",)


class RolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = ("id", "name")
