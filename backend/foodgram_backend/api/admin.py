from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    min_num = 1
    autocomplete_fields = ('ingredient',)

    def has_delete_permission(self, request, obj=None):
        """
        Проверяет, можно ли удалить ингредиенты.
        Если у рецепта меньше двух ингредиентов, запрещаем удаление.
        """
        if obj and obj.recipe_ingredients.count() <= 1:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'cooking_time')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    autocomplete_fields = ('tags', 'ingredients')
    inlines = [RecipeIngredientInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            try:
                obj.delete()
            except ValidationError as e:
                messages.warning(request, e.message)
                return None
        for instance in instances:
            instance.user = request.user
            instance.save()
        formset.save_m2m()


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')

    def delete_queryset(self, request, queryset):
        """
        Запрещает удаление последнего ингредиента рецепта через админку.
        """
        for obj in queryset:
            recipe = obj.recipe
            if recipe.recipe_ingredients.count() <= 1:
                raise ValidationError(
                    'Нельзя удалить последний ингредиент рецепта.'
                )
        super().delete_queryset(request, queryset)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
