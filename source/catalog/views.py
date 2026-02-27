# catalog/views.py
from __future__ import annotations

from rest_framework import serializers, status, views
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Category, Service


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "description", "image", "sort_order", "is_active")


class ServiceSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(source="category.id", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Service
        fields = (
            "id",
            "category_id",
            "category_name",
            "name",
            "description",
            "image",
            "base_price",
            "unit",
            "allow_multiple",
            "sort_order",
            "is_active",
        )


class CategoryListViewSet(ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by("sort_order", "name_ru")
    serializer_class = CategorySerializer


class CategoryServicesAPIView(views.APIView):
    """
    GET /api/categories/<category_id>/services/
    """

    def get(self, request, category_id: int):
        qs = Service.objects.filter(category_id=category_id).order_by("sort_order", "name_ru")
        data = ServiceSerializer(qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)
