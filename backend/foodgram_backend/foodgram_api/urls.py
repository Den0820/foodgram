from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CustomUserViewSet, TagViewSet, IngredientViewSet, RecipeViewSet

router = DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
    # path('auth/token/login/', CustomAuthToken.as_view()),
    # path('auth/token/logout/', LogoutView.as_view()),
]
