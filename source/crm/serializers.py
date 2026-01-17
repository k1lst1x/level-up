# crm/serializers.py
from rest_framework import serializers
from accounts.models import User
import secrets
import string


class CRMUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "name",
            "phone",
            "whatsapp",
            "email",
            "telegram",
            "company",
            "sphere",
            "tags_text",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined", "username"]

        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False, "allow_blank": True},
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
        }

    def get_name(self, obj):
        full = f"{obj.first_name} {obj.last_name}".strip()
        return full or obj.username

    def create(self, validated_data):
        phone = (validated_data.get("phone") or "").strip()

        # --- username ---
        if phone:
            base_username = phone.replace("+", "")
        else:
            base_username = "user"

        username = base_username
        i = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{i}"
            i += 1

        # --- random password ---
        alphabet = string.ascii_letters + string.digits
        raw_password = "".join(secrets.choice(alphabet) for _ in range(10))

        user = User(
            username=username,
            role=User.Role.CUSTOMER,
            **validated_data
        )
        user.set_password(raw_password)
        user.save()

        return user
