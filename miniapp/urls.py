from rest_framework import routers
from django.urls import path
from miniapp.views import BotClientViewset

router = routers.SimpleRouter()
router.register(r"botclient", BotClientViewset)
urlpatterns = router.urls
