# crm/views.py
from rest_framework import viewsets, permissions
from accounts.models import User
from .serializers import CRMUserSerializer


class CRMUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(role=User.Role.CUSTOMER).order_by("-date_joined")
    serializer_class = CRMUserSerializer
    permission_classes = [permissions.IsAuthenticated]
