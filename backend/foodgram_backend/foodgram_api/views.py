from rest_framework.viewsets import ViewSet
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import status
from users.models import MyUser, Subscription
from .pagination import CustomPagination
from .serializers import UserRegistraionSerializer, UserProfileSerializer, AvatarSerializer, PasswordChangeSerializer

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
        

