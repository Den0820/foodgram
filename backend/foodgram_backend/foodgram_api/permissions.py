from rest_framework.views import exception_handler
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.response import Response
from rest_framework import status, permissions


def custom_exception_handler(exc, context):
    # Получение стандартного ответа
    response = exception_handler(exc, context)

    # Проверяем, является ли ошибка NotAuthenticated
    if isinstance(exc, NotAuthenticated):
        return Response(
            {"detail": "Учетные данные не были предоставлены."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Проверяем, если это ошибка AuthenticationFailed
    if isinstance(exc, AuthenticationFailed):
        return Response(
            {"detail": "Ошибка аутентификации. Проверьте токен."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    return response


class IsAuthorOrAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return (request.method in permissions.SAFE_METHODS
                or request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return (request.method in permissions.SAFE_METHODS
                or obj.author == request.user
                or request.user.is_staff)