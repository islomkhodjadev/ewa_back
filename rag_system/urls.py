from django.urls import path
from rag_system.views import EmbeddingSearch

urlpatterns = [path("search/", EmbeddingSearch.as_view())]
