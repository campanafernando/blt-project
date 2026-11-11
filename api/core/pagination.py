from rest_framework.pagination import PageNumberPagination

PAGE_SIZE = 10


class StandardPagination(PageNumberPagination):
    page_size = PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = 100
