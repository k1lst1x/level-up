from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone


User = get_user_model()


class KPHomeTests(TestCase):
    def test_admin_customer_modal_shows_newest_accounts_first_and_has_search(self):
        admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            is_staff=True,
            role=User.Role.ADMIN,
        )
        oldest = User.objects.create_user(
            username="oldest",
            password="testpass123",
            phone="+70000000001",
        )
        middle = User.objects.create_user(
            username="middle",
            password="testpass123",
            phone="+70000000002",
        )
        newest = User.objects.create_user(
            username="newest",
            password="testpass123",
            phone="+70000000003",
        )

        now = timezone.now()
        User.objects.filter(pk=oldest.pk).update(date_joined=now - timedelta(days=3))
        User.objects.filter(pk=middle.pk).update(date_joined=now - timedelta(days=2))
        User.objects.filter(pk=newest.pk).update(date_joined=now - timedelta(days=1))

        self.client.force_login(admin)
        response = self.client.get(reverse("kp:kp"), {"tab": "active"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [user.username for user in response.context["customers"]],
            ["newest", "middle", "oldest"],
        )
        self.assertContains(response, 'id="kpCustomerSearchInput"')
        self.assertContains(response, "data-live-search-item", count=3)
