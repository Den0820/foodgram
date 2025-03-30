from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from users.models import MyUser, Subscription
from .serializers import UserRegistraionSerializer, SubscriptionSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404


class AuthView(generics.ListCreateAPIView):
    queryset = MyUser.objects.all()
    serializer_class = UserRegistraionSerializer
    permission_classes = [AllowAny]


class CustomAuthToken(ObtainAuthToken):

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
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            request.user.auth_token.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Token.DoesNotExist:
            return Response({"detail": "Некорректный токен."}, status=status.HTTP_400_BAD_REQUEST)
        


class UserViewSet(ViewSet):
    permission_classes = [AllowAny]

    # Эндпоинт для получения профиля пользователя
    def retrieve(self, request, pk=None):
        user = get_object_or_404(MyUser, pk=pk)
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }, status=status.HTTP_200_OK)

    # Эндпоинт для текущего пользователя
    @action(detail=False, methods=['get'], url_path='me')
    def get_current_user(self, request):
        user = request.user  # Текущий пользователь берется из токена
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }, status=status.HTTP_200_OK)

    # Эндпоинт для изменения пароля
    @action(detail=False, methods=['post'], url_path='set_password')
    def set_password(self, request):
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not current_password or not new_password:
            return Response({"detail": "Оба поля обязательны."}, status=status.HTTP_400_BAD_REQUEST)

        if not request.user.check_password(current_password):
            return Response({"detail": "Неверный текущий пароль."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Эндпоинт для работы с аватаром
    @action(detail=False, methods=['put'], url_path='me/avatar')
    def update_avatar(self, request):
        avatar = request.data.get('avatar')
        if avatar:
            request.user.avatar = avatar
            request.user.save()
            return Response({"avatar": request.user.avatar.url}, status=status.HTTP_200_OK)
        return Response({"detail": "Некорректные данные."}, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = SubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscribed_to = serializer.validated_data['subscribed_to']
        subscription, created = Subscription.objects.get_or_create(
            subscriber=request.user,
            subscribed_to=subscribed_to
        )
        if created:
            return Response({'detail': 'Подписка успешно создана'}, status=201)
        return Response({'detail': 'Вы уже подписаны на этого пользователя'}, status=400)

    def list(self, request):
        subscriptions = Subscription.objects.filter(subscriber=request.user)
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        subscription = Subscription.objects.filter(id=pk, subscriber=request.user).first()
        if subscription:
            subscription.delete()
            return Response({'detail': 'Подписка успешно удалена'}, status=204)
        return Response({'detail': 'Подписка не найдена'}, status=404)