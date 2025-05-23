from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from hashids import Hashids

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from djoser.views import UserViewSet

from users.models import MyUser, Subscription
from .constants import CUR_BASE_URL, MAX_LEN_SL
from .filters import IngredientFilter, RecipeFilter
from .models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from .pagination import CustomPagination
from .permissions import IsAuthorOrAdminOrReadOnly
from .serializers import (
    AvatarSerializer,
    CreateRecipeSerializer,
    IngredientSerializer,
    PasswordChangeSerializer,
    RecipeSerializer,
    SubscriptionCreateSerializer,
    SubscriptionSerializer,
    TagSerializer,
    UserProfileSerializer,
)

hashids = Hashids(min_length=MAX_LEN_SL, salt="your_secret_salt")


class CustomUserViewSet(UserViewSet):
    """
    ViewSet для работы с пользователями: регистрация, авторизация, профили.
    """
    queryset = MyUser.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPagination
    lookup_field = 'pk'

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """
        Эндпоинт GET /api/users/me/
        Получение данных текущего пользователя.
        """
        serializer = UserProfileSerializer(
            request.user, context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar',
    )
    def avatar(self, request):
        """
        Эндпоинт PUT и DELETE /api/users/me/avatar/
        Добавление или удаление аватара текущего пользователя.
        """
        user = request.user
        if request.method == 'PUT':
            if user.avatar:
                user.avatar.delete(save=False)
            serializer = AvatarSerializer(user, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=False)
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def set_password(self, request):
        """
        Эндпоинт POST /api/users/set_password/
        Изменение пароля текущего пользователя.
        """
        serializer = PasswordChangeSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe',
    )
    def subscribe(self, request, pk=None):
        """
        Подписаться на пользователя/
        Отписаться от пользователя.
        """
        subscriber = request.user.pk
        subscribed_to = get_object_or_404(MyUser, pk=pk).pk
        data = {
            'subscriber': subscriber,
            'subscribed_to': subscribed_to,
        }
        if request.method == 'POST':
            serializer = SubscriptionCreateSerializer(
                data=data, context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED
                )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                subscriber=subscriber, subscribed_to=subscribed_to
            ).first()
            if not subscription:
                return Response(
                    {'error': 'Подписка не найдена.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            subscription.delete()
            return Response(
                {'message': 'Подписка успешно удалена.'},
                status=status.HTTP_204_NO_CONTENT,
            )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions',
    )
    def subscriptions(self, request):
        """
        Получить список пользователей,
        на которых подписан текущий пользователь.
        """
        subscriptions = Subscription.objects.filter(subscriber=request.user)
        paginator = CustomPagination()
        page = paginator.paginate_queryset(subscriptions, request)
        if page is not None:
            serializer = SubscriptionSerializer(
                page, many=True, context={'request': request}
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            subscriptions, many=True, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class TagViewSet(ModelViewSet):
    """
    ViewSet для работы с тегами.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    http_method_names = ['get']


class IngredientViewSet(ModelViewSet):
    """
    ViewSet для работы с ингредиентами.
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    http_method_names = ['get']
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    permission_classes = [AllowAny]


class RecipeViewSet(ModelViewSet):
    """
    ViewSet для работы с рецептами.
    """
    queryset = Recipe.objects.all()
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    search_fields = ('^name',)
    permission_classes = [IsAuthorOrAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'list':
            return RecipeSerializer
        return CreateRecipeSerializer

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[AllowAny],
        url_path='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        if not recipe.short_url:
            recipe.short_url = hashids.encode(recipe.id)
            recipe.save()
        short_link = f'{CUR_BASE_URL}s/{recipe.short_url}'
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        """
        Добавление и удаление рецепта из списка покупок.
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            if ShoppingCart.objects.filter(
                user=request.user,
                recipe=recipe
            ).exists():
                return Response(
                    {'error': 'Рецепт уже находится в списке покупок.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            return Response(
                {
                    'id': recipe.id,
                    'name': recipe.name,
                    'image': recipe.image.url,
                    'cooking_time': recipe.cooking_time,
                },
                status=status.HTTP_201_CREATED,
            )
        elif request.method == 'DELETE':
            shopping_cart_entry = ShoppingCart.objects.filter(
                user=request.user, recipe=recipe
            ).first()
            if not shopping_cart_entry:
                return Response(
                    {'error': 'Рецепта нет в списке покупок.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            shopping_cart_entry.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        """
        Скачивание списка покупок.
        """
        shopping_cart = ShoppingCart.objects.filter(user=request.user)
        if not shopping_cart.exists():
            return Response(
                {'detail': 'Ваш список покупок пуст.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content = []
        for item in shopping_cart:
            for ingredient in item.recipe.recipe_ingredients.all():
                content.append(
                    f'{ingredient.ingredient.name} - '
                    f'{ingredient.amount} '
                    f'{ingredient.ingredient.measurement_unit}'

                )

        response = Response(
            '\n'.join(content),
            content_type='text/plain',
            status=status.HTTP_200_OK,
        )
        response['Content-Disposition'] = (
            'attachment; filename='
            'shopping_cart.txt'
        )

        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='favorite',
    )
    def favorite(self, request, pk=None):
        """
        Добавление и удаление рецепта из списка избранного.
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            if Favorite.objects.filter(
                user=request.user,
                recipe=recipe
            ).exists():
                return Response(
                    {'error': 'Рецепт уже находится в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Favorite.objects.create(user=request.user, recipe=recipe)
            return Response(
                {
                    'id': recipe.id,
                    'name': recipe.name,
                    'image': recipe.image.url,
                    'cooking_time': recipe.cooking_time,
                },
                status=status.HTTP_201_CREATED,
            )
        elif request.method == 'DELETE':
            favorite_entry = Favorite.objects.filter(
                user=request.user, recipe=recipe
            ).first()
            if not favorite_entry:
                return Response(
                    {'error': 'Рецепт отсутствует в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            favorite_entry.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
