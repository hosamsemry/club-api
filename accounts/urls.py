from django.urls import path
from .views import RegisterView, ClubUserViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'register', RegisterView, basename='register')
router.register(r'users', ClubUserViewSet, basename='clubuser')

urlpatterns = router.urls