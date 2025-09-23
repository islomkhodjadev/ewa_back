from django.urls import path
from rag_system.views import EmbeddingSearch, GetRolesView

urlpatterns = [path("roles/", GetRolesView.as_view())]
