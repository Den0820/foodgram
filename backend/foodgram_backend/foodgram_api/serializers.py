import base64

from django.core.files.base import ContentFile
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers
from djoser.serializers import UserCreateSerializer, UserSerializer

from .models import Tag, Ingredient, Recipe, RecipeIngredient
from users.models import MyUser, Subscription


class Base64ImageField(serializers.ImageField):
    """
    Поле для обработки изображений в формате Base64.
    """
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UserRegistraionSerializer(UserCreateSerializer):
    """
    Сериализатор для регистрации пользователей.
    """
    password = serializers.CharField(write_only=True)

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
            raise serializers.ValidationError('Невозможное имя пользователя')
        if MyUser.objects.filter(email=data.get('email')).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже существует'
            )
        return data


class UserProfileSerializer(UserSerializer):
    """
    Сериализатор профиля пользователя.
    """
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = MyUser
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name',
            'is_subscribed', 'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                subscriber=request.user, subscribed_to=obj
            ).exists()
        return False


class AvatarSerializer(serializers.ModelSerializer):
    """
    Сериализатор для аватара пользователя.
    """
    avatar = Base64ImageField(required=True, allow_null=True)

    class Meta:
        model = MyUser
        fields = ('avatar',)


class PasswordChangeSerializer(serializers.Serializer):
    """
    Сериализатор для изменения пароля.
    """
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
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
    """
    Сериализатор для тегов.
    """
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ингредиентов.
    """
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')

    def validate_amount(self, value):
        """
        Проверяет, что количество ингредиента больше минимального значения.
        """
        if value <= 0:
            raise serializers.ValidationError(
                'Количество ингредиента должно быть больше нуля.'
            )
        return value


class RecipeIngredientSerializer(serializers.Serializer):
    """
    Сериализатор для обработки ингредиентов в рецепте.
    """
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
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
                'Количество ингредиента должно быть больше нуля.'
            )
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
        many=True, source='recipe_ingredients'
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'tags',
            'text', 'image', 'author',
            'cooking_time', 'is_favorited',
            'is_in_shopping_cart', 'ingredients',
        )
        read_only_fields = (
            'tags', 'author', 'is_favorited', 'is_in_shopping_cart',
        )

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)
        if fields:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

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

    ingredients = RecipeIngredientCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        read_only=False,
    )
    author = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault(),
    )

    def validate_tags(self, value):
        tags = []
        if not value:
            raise serializers.ValidationError('Добавьте теги.')
        for tag in value:
            if tag.id in tags:
                raise serializers.ValidationError('Этот тег уже добавлен.')
            tags.append(tag.id)
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
        print(value)
        return value

    def validate_cooking_time(self, value):
        """
        Проверка корректности времени приготовления рецепта.
        """
        if value <= 0:
            raise serializers.ValidationError(
                'Время приготовления должно быть больше 0 минут.'
            )
        return value

    @staticmethod
    def create_ingredients(ingredients, recipe):
        for ingredient_data in ingredients:
            RecipeIngredient.objects.create(
                ingredient=ingredient_data.pop('id'),
                amount=ingredient_data.pop('amount'),
                recipe=recipe,
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
        ingredients = validated_data.pop('ingredients', [])
        tags = validated_data.pop('tags', [])

        if not ingredients or not tags:
            raise serializers.ValidationError(
                'Ингредиенты или теги не указаны.'
            )
        instance.tags.clear()
        instance.ingredients.clear()
        instance.tags.set(tags)
        self.create_ingredients(ingredients, instance)
        return instance

    def to_representation(self, instance):
        return RecipeSerializer(
            instance, context={'request': self.context.get('request')},
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
        subscription = Subscription.objects.create(
            subscriber=subscriber,
            subscribed_to=subscribed_to,
        )
        return subscription

    def validate(self, data):
        subscriber = data.get('subscriber')
        subscribed_to = data.get('subscribed_to')
        if subscriber == subscribed_to:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.'
            )
        if Subscription.objects.filter(
            subscriber=subscriber, subscribed_to=subscribed_to,
        ).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя.'
            )
        return data

    def to_representation(self, instance):
        return SubscriptionSerializer(instance, context=self.context).data


class SubscriptionSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source='subscribed_to.email',
        read_only=True
    )
    id = serializers.IntegerField(source='subscribed_to.id', read_only=True)
    username = serializers.CharField(
        source='subscribed_to.username', read_only=True,
    )
    first_name = serializers.CharField(
        source='subscribed_to.first_name', read_only=True,
    )
    last_name = serializers.CharField(
        source='subscribed_to.last_name', read_only=True,
    )
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(
        source='subscribed_to.avatar', read_only=True,
    )
    recipes_count = serializers.IntegerField(
        source='subscribed_to.recipes.count', read_only=True,
    )
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar',
        )

    def get_recipes(self, obj):
        request = self.context['request']
        limit = request.GET.get('recipes_limit')
        recipes = obj.subscribed_to.recipes.all()
        if limit:
            try:
                limit = int(limit)
            except ValueError:
                raise serializers.ValidationError(
                    'recipes_limit должен быть числом.'
                )
            recipes = recipes[:limit]
        return RecipeSerializer(
            recipes, many=True, context=self.context,
            fields=('id', 'name', 'image', 'cooking_time'),
        ).data

    def get_recipes_count(self, obj):
        return obj.subscribed_to.recipes.count()

    def get_is_subscribed(self, obj):
        """
        Проверяет, подписан ли текущий пользователь на данного пользователя.
        """
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(
            subscriber=request.user, subscribed_to=obj.subscribed_to,
        ).exists()
