from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
    page_size = 10  # Количество объектов по умолчанию
    page_size_query_param = 'limit'  # Позволяет изменять количество объектов через параметр запроса
    max_page_size = 100  # Максимальное количество объектов на странице

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })