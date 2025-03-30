from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views

from .views import AuthView, CustomAuthToken, LogoutView, SubscriptionViewSet

router = DefaultRouter()
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')


urlpatterns = [
    path('users/', AuthView.as_view()),
    path('auth/token/login/', CustomAuthToken.as_view()),
    path('auth/token/logout/', LogoutView.as_view()),
    path('api/', include(router.urls)),
]