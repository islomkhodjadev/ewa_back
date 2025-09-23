from django.shortcuts import render

# Create your views here.

from rest_framework import views
from rag_system.utils.search import search_documents
from rag_system.serializers import EmbeddingSerializer, RolesSerializer
from rest_framework.views import APIView, Response
from rag_system.models import Roles


class EmbeddingSearch(views.APIView):

    def post(self, request):
        data = request.data
        prompt = data.get("prompt")

        if prompt is None:
            return views.Response(
                {"status": "error"}, status=views.status.HTTP_400_BAD_REQUEST
            )
        data = search_documents(prompt)
        print(data)
        return views.Response(
            data=EmbeddingSerializer(data, many=True).data,
            status=views.status.HTTP_200_OK,
        )


class GetRolesView(APIView):

    def post(self, request, *args, **kwargs):
        roles = Roles.objects.all()

        return Response(data=RolesSerializer(roles, many=True).data)
