from django.urls import path
from .views import RegisterView
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'register', RegisterView, basename='register')

urlpatterns = router.urls