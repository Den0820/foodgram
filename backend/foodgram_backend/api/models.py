from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .constants import (
    MAX_INGRED_LENGTH,
    MAX_LEN_SL,
    MAX_MU_LENGTH,
    MAX_RN_LENGTH,
    MAX_TEG_LENGTH
)

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(max_length=MAX_TEG_LENGTH, unique=True)
    slug = models.SlugField(max_length=MAX_TEG_LENGTH, unique=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=MAX_INGRED_LENGTH)
    measurement_unit = models.CharField(max_length=MAX_MU_LENGTH)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes'
    )
    name = models.CharField(max_length=MAX_RN_LENGTH)
    text = models.TextField()
    cooking_time = models.PositiveIntegerField()
    image = models.ImageField(
        null=False,
        blank=False,
        upload_to='recipes/images/'
    )
    tags = models.ManyToManyField(Tag, related_name='recipes')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes'
    )
    short_url = models.CharField(
        max_length=MAX_LEN_SL,
        unique=True,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_recipes'
    )
    amount = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.amount} {self.ingredient.name} для {self.recipe.name}'

    def delete(self, *args, **kwargs):
        """
        Запрещаем удаление ингредиента, если он последний у рецепта.
        """
        if self.recipe.recipe_ingredients.count() <= 1:
            raise ValidationError(
                'Не получилось удалить последний ингредиент у рецепта.'
            )
        super().delete(*args, **kwargs)


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'user'],
                name='unique_favorite_recipe_user'
            )
        ]

    def __str__(self):
        return f'{self.user.username} добавил {self.recipe.name} в избранное'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_cart'
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'user'],
                name='unique_shopping_cart_recipe_user'
            )
        ]

    def __str__(self):
        return (
            f'{self.user.username} добавил {self.recipe.name} в список покупок'
        )
