from django.core import validators
from rest_framework import serializers, status
from rest_framework.response import Response

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


class UserRegistraionSerializer(serializers.ModelSerializer):

    class Meta:
        model = MyUser
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password'
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
    subscriber = serializers.StringRelatedField(read_only=True)
    subscribed_to = serializers.PrimaryKeyRelatedField(queryset=MyUser.objects.all())

    class Meta:
        model = Subscription
        fields = ['id', 'subscriber', 'subscribed_to', 'created_at']

    def validate_subscribed_to(self, value):
        if self.context['request'].user == value:
            raise serializers.ValidationError("Вы не можете подписаться на самого себя.")
        return value


class UserSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = MyUser
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed', 'avatar',
            'image'
        )
