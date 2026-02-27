from rest_framework import serializers
from catalog.models import Service
from .models import Proposal, ProposalItem, KPTemplate


class KPTemplateShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPTemplate
        fields = ["id", "name"]


class ProposalItemSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = ProposalItem
        fields = ["id", "service", "service_name", "qty", "price", "total_price"]
        read_only_fields = ["total_price"]


class ProposalSerializer(serializers.ModelSerializer):
    template = KPTemplateShortSerializer(read_only=True)
    items = ProposalItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Proposal
        fields = ["id", "title", "status", "notes", "template", "items", "total_amount", "created_at", "updated_at"]
