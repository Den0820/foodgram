from django.core import validators
from rest_framework import serializers, status
from rest_framework.response import Response
from django.contrib.auth.password_validation import validate_password
from djoser.serializers import UserCreateSerializer, UserSerializer
from .models import Tag, Ingredient, Recipe, RecipeIngredient


import base64

from django.core.files.base import ContentFile

from users.models import MyUser, Subscription


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class UserRegistraionSerializer(UserCreateSerializer):
    password = serializers.CharField(
        write_only=True
    )

    class Meta:
        model = MyUser
        fields = (
            'email',
            'first_name',
            'id',
            'last_name',
            'password',
            'username',
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }


    def validate(self, data):
        if data.get('username') == 'me':
            raise serializers.ValidationError(
                'Невозможное имя пользователя'
            )
        if MyUser.objects.filter(email=data.get('email')).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже существует'
            )
        return data


class SubscriptionSerializer(serializers.ModelSerializer):
    subscribed_to = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ['subscribed_to', 'recipes', 'recipes_count']

    def get_subscribed_to(self, obj):
        user = obj.subscribed_to
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar": user.avatar.url if user.avatar else None,
        }

    def get_recipes(self, obj):
        recipes_limit = self.context['request'].query_params.get('recipes_limit')
        recipes = obj.subscribed_to.recipes.all()
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        return RecipeSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.subscribed_to.recipes.count()


class UserProfileSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = MyUser
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(subscriber=request.user, subscribed_to=obj).exists()
        return False


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True, allow_null=True)

    class Meta:
        model = MyUser
        fields = ('avatar',)


class PasswordChangeSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    current_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.Serializer):
    """
    Сериализатор для обработки ингредиентов в рецепте.
    """
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'name', 'measurement_unit', 'amount']

    def validate_amount(self, value):
        """
        Проверяет, что количество ингредиента больше минимального значения.
        """
        if value <= 0:
            raise serializers.ValidationError(
                'Количество ингредиента должно быть больше нуля.')
        return value


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения списка рецептов.
    """
    image = Base64ImageField()
    author = UserProfileSerializer()
    tags = TagSerializer(many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipe_ingredients')

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'tags',
            'text', 'image', 'author',
            'cooking_time', 'is_favorited',
            'is_in_shopping_cart', 'ingredients'
        )
        read_only_fields = (
            'tags', 'author', 'is_favorited', 'is_in_shopping_cart'
        )

    def get_ingredients(self, obj):
        ingredients = RecipeIngredient.objects.filter(recipe=obj.id)
        return RecipeIngredientSerializer(ingredients, many=True).data

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.favorites.filter(recipe=obj.id).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.shopping_cart.filter(recipe=obj.id).exists()


class CreateRecipeSerializer(RecipeSerializer):
    """
    Сериализатор для создания рецепта.
    """

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    ingredients = RecipeIngredientSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        read_only=False
    )
    author = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError('Добавьте теги.')
        return value

    def validate_ingredients(self, value):
        ingredients = []
        if not value:
            raise serializers.ValidationError('Добавьте ингредиенты.')
        for ingredient in value:
            if ingredient.get('id') in ingredients:
                raise serializers.ValidationError(
                    'Этот ингредиент уже добавлен.'
                )
            ingredients.append(ingredient.get('id'))
        return value
    
    def validate_cooking_time(self, value):
        """
        Проверка корректности времени
        приготовления рецепта.
        """

        if value <= 0:
            raise ValidationError(
                f'Время приготовления должно быть больше 0 минут.'
            )
        return value

    @staticmethod
    def create_ingredients(ingredients, recipe):
        for ingredient_data in ingredients:
            RecipeIngredient.objects.create(
                ingredient=ingredient_data.pop('id'),
                amount=ingredient_data.pop('amount'),
                recipe=recipe
            )

    def create(self, validated_data):
        author = self.context.get('request').user
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        instance.tags.clear()
        instance.ingredients.clear()
        instance.tags.set(validated_data.pop('tags'))
        ingredients = validated_data.pop('ingredients')
        self.create_ingredients(ingredients, instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeSerializer(
            instance, context={'request': self.context.get('request')}
        ).data


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор подписки пользователя.
    """

    class Meta:
        model = Subscription
        fields = ('subscriber', 'subscribed_to')

    def create(self, validated_data):
        subscriber = validated_data['subscriber']
        subscribed_to = validated_data['subscribed_to']

        subscription = Subscription.objects.create(subscriber=subscriber, subscribed_to=subscribed_to)
        return "Подписка успешно создана."

    def validate(self, data):
        subscriber = data.get('subscriber')
        subscribed_to = data.get('subscribed_to')

        if subscriber == subscribed_to:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.'
            )

        if Subscription.objects.filter(subscriber=subscriber, subscribed_to=subscribed_to).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя.'
            )
        return data