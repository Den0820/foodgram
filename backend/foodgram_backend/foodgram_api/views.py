from rest_framework.viewsets import ViewSet, ModelViewSet
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authtoken.models import Token
from rest_framework.filters import SearchFilter
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import status
from users.models import MyUser, Subscription
from .models import Tag, Ingredient, Recipe, ShoppingCart, Favorite
from .pagination import CustomPagination
from .serializers import UserRegistraionSerializer, UserProfileSerializer, AvatarSerializer, PasswordChangeSerializer, TagSerializer, IngredientSerializer, RecipeSerializer, CreateRecipeSerializer, SubscriptionSerializer
from .filters import RecipeFilter
from .permissions import IsAuthorOrAdminOrReadOnly

class UserViewSet(ViewSet):
    """
    ViewSet для работы с пользователями: регистрация, авторизация, профили.
    """
    permission_classes = [AllowAny]

    def list(self, request):
        """
        Эндпоинт GET /api/users/
        Возвращает список пользователей с поддержкой пагинации.
        """
        queryset = MyUser.objects.all()
        paginator = CustomPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = UserProfileSerializer(paginated_queryset, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def create(self, request):
        """
        Эндпоинт POST /api/users/
        Регистрация нового пользователя.
        """
        serializer = UserRegistraionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """
        Эндпоинт GET /api/users/<id>/
        Получение публичного профиля пользователя.
        """
        user = get_object_or_404(MyUser, pk=pk)
        serializer = UserProfileSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Эндпоинт GET /api/users/me/
        Получение данных текущего пользователя.
        """
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'delete'], permission_classes=[IsAuthenticated], url_path='me/avatar')
    def avatar(self, request):
        """
        Эндпоинт PUT и DELETE /api/users/me/avatar/
        Добавление или удаление аватара текущего пользователя.
        """
        user = request.user
        if request.method == 'PUT':
            if user.avatar:
                user.avatar.delete(save=False)  # Удаляем старый файл, если он существует
            serializer = AvatarSerializer(user, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=False)  # Удаляем файл
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def set_password(self, request):
        """
        Эндпоинт POST /api/users/set_password/
        Изменение пароля текущего пользователя.
        """
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='subscriptions')
    def subscriptions(self, request):
        """
        Получить список пользователей, на которых подписан текущий пользователь.
        """
        subscriptions = Subscription.objects.filter(subscriber=request.user)
        paginator = CustomPagination()  # Используем экземпляр класса пагинации
        page = paginator.paginate_queryset(subscriptions, request)  # Пагинация вручную
        if page is not None:
            serializer = SubscriptionSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
    
        serializer = SubscriptionSerializer(subscriptions, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated], url_path='subscribe')
    def subscribe(self, request, pk=None):
        """
        Подписаться на пользователя/
        Отписаться от пользователя.
        """
        user = get_object_or_404(MyUser, pk=pk)
        if request.method == 'POST':
            if user == request.user:
                return Response({"error": "Нельзя подписаться на себя."}, status=status.HTTP_400_BAD_REQUEST)

            if Subscription.objects.filter(subscriber=request.user, subscribed_to=user).exists():
                return Response({"error": "Вы уже подписаны на этого пользователя."}, status=status.HTTP_400_BAD_REQUEST)

            subscription = Subscription.objects.create(subscriber=request.user, subscribed_to=user)
            serializer = SubscriptionSerializer(subscription, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(subscriber=request.user, subscribed_to=user).first()
            if not subscription:
                return Response({"error": "Вы не подписаны на этого пользователя."}, status=status.HTTP_400_BAD_REQUEST)

            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class CustomAuthToken(ObtainAuthToken):
    """
    ViewSet для авторизации пользователя путем выдачи токена.
    """

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'auth_token': token.key,
        })


class LogoutView(APIView):
    """
    ViewSet для завершения сессии текущего пользователя.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            request.user.auth_token.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Token.DoesNotExist:
            return Response({"detail": "Некорректный токен."}, status=status.HTTP_400_BAD_REQUEST)


class TagViewSet(ModelViewSet):
    """
    ViewSet для работы с тегами.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ['get']


class IngredientViewSet(ModelViewSet):
    """
    ViewSet для работы с ингредиентами.
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    http_method_names = ['get']
    filter_backends = [SearchFilter]
    search_fields = ['^name']


class RecipeViewSet(ModelViewSet):
    """Вывод работы с рецептами."""
    queryset = Recipe.objects.all()
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, ]
    filterset_class = RecipeFilter
    search_fields = ('^name', )
    permission_classes = (IsAuthorOrAdminOrReadOnly, )

    def get_serializer_class(self):
        if self.action == 'list':
            return RecipeSerializer
        return CreateRecipeSerializer
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = f"https://foodgram.example.org/s/{recipe.id}"
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)


    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated], url_path='shopping_cart')
    def shopping_cart(self, request, pk=None):
        """
       Добавление и удаление рецепта из списка покупок.
       """
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=request.user, recipe=recipe).exists():
                return Response(
                    {"error": "Рецепт уже находится в списке покупок."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            return Response(
                {"id": recipe.id, "name": recipe.name, "image": recipe.image.url, "cooking_time": recipe.cooking_time},
                status=status.HTTP_201_CREATED
            )
        elif request.method == 'DELETE':
            shopping_cart_entry = ShoppingCart.objects.filter(user=request.user, recipe=recipe).first()
            if not shopping_cart_entry:
                return Response(
                    {"error": "Рецепта нет в списке покупок."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            shopping_cart_entry.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """
        Скачивание списка покупок.
        """
        shopping_cart = ShoppingCart.objects.filter(user=request.user)
        if not shopping_cart.exists():
            return Response({"detail": "Ваш список покупок пуст."}, status=status.HTTP_400_BAD_REQUEST)

        content = []
        for item in shopping_cart:
            for ingredient in item.recipe.recipe_ingredients.all():  # Используем корректный related_name
                content.append(f"{ingredient.ingredient.name} - {ingredient.amount} {ingredient.ingredient.measurement_unit}")

        response = Response(
            "\n".join(content),
            content_type='text/plain',
            status=status.HTTP_200_OK
        )
        response['Content-Disposition'] = 'attachment; filename="shopping_cart.txt"'
        return response

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated], url_path='favorite')
    def favorite(self, request, pk=None):
        """
        Добавление и удаление рецепта из списка избранного.
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        
        if request.method == 'POST':
            # Проверка на наличие рецепта в списке избранного
            if Favorite.objects.filter(user=request.user, recipe=recipe).exists():
                return Response(
                    {"error": "Рецепт уже находится в избранном."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Добавление в избранное
            Favorite.objects.create(user=request.user, recipe=recipe)
            return Response(
                {"id": recipe.id, "name": recipe.name, "image": recipe.image.url, "cooking_time": recipe.cooking_time},
                status=status.HTTP_201_CREATED
            )
        
        elif request.method == 'DELETE':
            # Удаление из списка избранного
            favorite_entry = Favorite.objects.filter(user=request.user, recipe=recipe).first()
            if not favorite_entry:
                return Response(
                    {"error": "Рецепт отсутствует в избранном."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            favorite_entry.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
