from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .constants import (
    DEF_PAGE_SIZE,
    MAX_PAGE_SIZE
)


class CustomPagination(PageNumberPagination):
    """
    Кастомный класс пагинации для настройки количества объектов на странице.
    """
    page_size = DEF_PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = MAX_PAGE_SIZE

    def get_paginated_response(self, data):
        """
        Возвращает ответ с пагинацией.
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })
