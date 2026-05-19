from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import TestCase

from main import moderation
from main.models import Device, DeviceBan


class ModerationServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username="mod-test-user")

    def test_device_ban_result_uses_cache_and_invalidation(self):
        self.assertFalse(moderation.get_device_ban_result("device-1").banned)

        DeviceBan.objects.create(
            fingerprint="device-1",
            active=True,
            reason="test reason",
            related_user=self.user,
        )

        self.assertFalse(moderation.get_device_ban_result("device-1").banned)

        moderation.invalidate_device_ban_cache("device-1")
        result = moderation.get_device_ban_result("device-1")

        self.assertTrue(result.banned)
        self.assertEqual(result.reason, "test reason")
        self.assertEqual(result.fingerprint, "device-1")

    def test_create_device_bans_for_user_bans_all_known_devices(self):
        Device.objects.create(fingerprint="last-user-device", last_user=self.user)
        usage_device = Device.objects.create(fingerprint="usage-device")
        usage_device.usages.create(user=self.user)

        created_count = moderation.create_device_bans_for_user(
            self.user,
            reason="linked devices",
        )

        self.assertEqual(created_count, 2)
        self.assertEqual(
            set(DeviceBan.objects.filter(active=True).values_list("fingerprint", flat=True)),
            {"last-user-device", "usage-device"},
        )
