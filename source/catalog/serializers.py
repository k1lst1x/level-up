# catalog/serializers.py
from rest_framework import serializers
from .models import Category, Subcategory, Service


class CategorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "description", "image_url", "sort_order", "is_active"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if not getattr(obj, "image", None):
            return None
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class SubcategorySerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(source="category.id", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Subcategory
        fields = ["id", "category_id", "name", "description", "image_url", "sort_order", "is_active"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if not getattr(obj, "image", None):
            return None
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class ServiceSerializer(serializers.ModelSerializer):
    subcategory_id = serializers.IntegerField(source="subcategory.id", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "subcategory_id",
            "name",
            "description",
            "base_price",
            "unit",
            "image_url",
            "sort_order",
            "is_active",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if not getattr(obj, "image", None):
            return None
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url
