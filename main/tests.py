from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import TestCase

from main import moderation
from fleet.models import liverie, reservedOperatorName
from main.models import Device, DeviceBan, featureToggle


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


class LiveryReservationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = get_user_model().objects.create_user(username="reservation-owner")
        self.other_user = get_user_model().objects.create_user(username="livery-user")
        featureToggle.objects.create(name="add_livery", enabled=True)

    def test_create_livery_blocks_reserved_operator_name_for_other_users(self):
        reservedOperatorName.objects.create(operator_name="Reserved Bus", owner=self.owner)
        self.client.force_login(self.other_user)

        response = self.client.post('/create/livery/', {
            'livery-name': 'rEsErVeD bUs',
            'livery-colour': '#123456',
            'livery-css-left': '',
            'livery-css-right': '',
            'text-colour': '#ffffff',
            'text-stroke-colour': '#000000',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "This operator name (Reserved Bus) is reserved, if you think this is a mistake please open a ticket via discord or on the site",
        )
        self.assertFalse(liverie.objects.filter(name__iexact="Reserved Bus").exists())
