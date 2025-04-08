from django_filters import rest_framework as filters
from .models import Recipe

class RecipeFilter(filters.FilterSet):
    """
    Фильтр для рецептов.
    """
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(method='filter_is_in_shopping_cart')
    author = filters.NumberFilter(field_name='author__id')
    tags = filters.CharFilter(field_name='tags__slug', method='filter_tags', lookup_expr='iexact')

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']

    def filter_is_favorited(self, queryset, name, value):
        """
        Фильтрация по избранным рецептам текущего пользователя.
        """
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()  # Если пользователь не авторизован
        if value:
            return queryset.filter(favorited_by__id=user.id)
        return queryset.exclude(favorited_by__id=user.id)

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """
        Фильтрация по рецептам, добавленным в список покупок текущего пользователя.
        """
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()  # Если пользователь не авторизован
        if value:
            return queryset.filter(in_shopping_cart__id=user.id)
        return queryset.exclude(in_shopping_cart__id=user.id)

    def filter_tags(self, queryset, name, value):
        """
        Фильтрация по тегам (можно указать несколько тегов через запятую).
        """
        tags = value.split(',')
        return queryset.filter(tags__slug__in=tags).distinct()