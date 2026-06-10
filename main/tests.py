from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from unittest.mock import patch

from main import moderation
from main.context_processors import theme_settings
from main.discord_roles import (
    discord_boost_subscription_id,
    sync_discord_ad_free_role,
    sync_discord_booster_subscription,
    user_is_discord_booster,
)
from fleet.models import liverie, reservedOperatorName
from main.models import ActiveSubscription, Device, DeviceBan, featureToggle
from mybustimes.middleware.rest_last_active import UpdateLastActiveMiddleware


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


class DiscordBoosterAdFreeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="discord-booster",
            discord_id="123456789012345678",
        )

    @override_settings(
        DISCORD_BOOSTER_AD_FREE_ENABLED=True,
        DISCORD_GUILD_ID="guild-1",
        DISCORD_BOT_TOKEN="token-1",
    )
    @patch("main.discord_roles.requests.get")
    def test_user_is_discord_booster_uses_member_premium_since(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"premium_since": "2026-06-11T00:00:00.000000+00:00"}

        self.assertTrue(user_is_discord_booster(self.user, use_cache=False))
        mock_get.assert_called_once()

    @override_settings(
        DISCORD_BOOSTER_AD_FREE_ENABLED=True,
        DISCORD_GUILD_ID="guild-1",
        DISCORD_BOT_TOKEN="token-1",
    )
    @patch("main.context_processors.user_is_discord_booster", return_value=True)
    def test_discord_booster_disables_ads_without_granting_pro(self, mock_booster):
        featureToggle.objects.create(name="ads", enabled=True)
        featureToggle.objects.create(name="google_ads", enabled=True)
        featureToggle.objects.create(name="mbt_ads", enabled=True)

        request = RequestFactory().get("/")
        request.user = self.user

        context = theme_settings(request)

        self.assertFalse(context["ads_enabled"])
        self.assertFalse(context["google_ads_enabled"])
        self.assertFalse(context["mbt_ads_enabled"])
        self.assertTrue(context["is_discord_booster"])
        self.assertEqual(context["has_pro"], "false")
        mock_booster.assert_called_once_with(self.user)

    @patch("mybustimes.middleware.rest_last_active.user_is_discord_booster")
    @patch("mybustimes.middleware.rest_last_active.sync_discord_ad_free_role")
    def test_active_linked_user_refreshes_discord_booster_status(self, mock_ad_free_sync, mock_booster):
        mock_booster.return_value = True
        cache.set(f"u_sub:{self.user.id}", (True, False, False), 300)
        self.user.last_active = timezone.now() - timezone.timedelta(minutes=2)
        self.user.save(update_fields=["last_active"])

        request = RequestFactory().get("/")
        request.user = self.user

        middleware = UpdateLastActiveMiddleware(lambda req: None)
        middleware.process_view(request, lambda req: None, (), {})

        self.assertIsNone(cache.get(f"u_sub:{self.user.id}"))
        mock_booster.assert_called_once_with(self.user, use_cache=False)
        mock_ad_free_sync.assert_called_once_with(self.user, True)
        self.assertTrue(
            ActiveSubscription.objects.filter(
                stripe_subscription_id="BOOST:123456789012345678",
                user=self.user,
                end_date__gt=timezone.now(),
                plan="basic",
            ).exists()
        )

    def test_sync_discord_booster_subscription_creates_boost_subscription(self):
        subscription = sync_discord_booster_subscription(self.user, True)

        self.assertEqual(subscription.stripe_subscription_id, "BOOST:123456789012345678")
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.plan, "basic")
        expected_date = timezone.localdate() + timezone.timedelta(days=1)
        local_end = timezone.localtime(subscription.end_date)
        self.assertEqual(local_end.date(), expected_date)
        self.assertEqual((local_end.hour, local_end.minute, local_end.second), (23, 59, 59))

    def test_sync_discord_booster_subscription_ends_subscription_on_unboost(self):
        sync_discord_booster_subscription(self.user, True)

        subscription = sync_discord_booster_subscription(self.user, False)

        self.assertEqual(subscription.stripe_subscription_id, discord_boost_subscription_id(self.user.discord_id))
        self.assertLessEqual(subscription.end_date, timezone.now())

    @override_settings(
        DISCORD_GUILD_ID="guild-1",
        DISCORD_BOT_TOKEN="token-1",
        DISCORD_AD_FREE_ROLE_ID="role-1",
    )
    @patch("main.discord_roles.requests.put")
    def test_sync_discord_ad_free_role_adds_role(self, mock_put):
        mock_put.return_value.status_code = 204

        self.assertTrue(sync_discord_ad_free_role(self.user, True))
        mock_put.assert_called_once()
        self.assertIn(
            "/guilds/guild-1/members/123456789012345678/roles/role-1",
            mock_put.call_args.args[0],
        )

    @override_settings(
        DISCORD_GUILD_ID="guild-1",
        DISCORD_BOT_TOKEN="token-1",
        DISCORD_AD_FREE_ROLE_ID="role-1",
    )
    @patch("main.discord_roles.requests.delete")
    def test_sync_discord_ad_free_role_removes_role(self, mock_delete):
        mock_delete.return_value.status_code = 204

        self.assertTrue(sync_discord_ad_free_role(self.user, False))
        mock_delete.assert_called_once()
        self.assertIn(
            "/guilds/guild-1/members/123456789012345678/roles/role-1",
            mock_delete.call_args.args[0],
        )
