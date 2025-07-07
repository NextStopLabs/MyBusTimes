from django.test import TestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from .models import (
    badge, MBTAdminPermission, theme, ad, google_ad, CustomUser,
    BannedIps, region, siteUpdate, update, Report, featureToggle
)

User = get_user_model()

class ModelTests(TestCase):
    def setUp(self):
        self.badge = badge.objects.create(
            badge_name="Test Badge",
            badge_backgroud="#000000",
            badge_text_color="#FFFFFF",
            additional_css="font-weight: bold;",
            self_asign=True
        )

        self.permission = MBTAdminPermission.objects.create(
            name="Can Manage Users",
            description="Allow management of users"
        )

        self.theme = theme.objects.create(
            theme_name="Dark Theme",
            css=SimpleUploadedFile("theme.css", b"body { background: #000; }"),
            main_colour="#000000",
            dark_theme=True,
            weight=1
        )

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            theme=self.theme,
            ticketer_code='TKT123'
        )
        self.user.badges.add(self.badge)
        self.user.mbt_admin_perms.add(self.permission)

    def test_badge_str(self):
        self.assertEqual(str(self.badge), "Test Badge")

    def test_permission_str(self):
        self.assertEqual(str(self.permission), "Can Manage Users")

    def test_theme_str(self):
        self.assertEqual(str(self.theme), "Dark Theme - Dark - 1")

    def test_user_str(self):
        self.assertEqual(str(self.user), "testuser")

    def test_user_badge_relation(self):
        self.assertIn(self.badge, self.user.badges.all())

    def test_user_permission_relation(self):
        self.assertIn(self.permission, self.user.mbt_admin_perms.all())

    def test_user_is_ad_free(self):
        self.user.ad_free_until = timezone.now() + timezone.timedelta(days=1)
        self.assertTrue(self.user.is_ad_free())

    def test_user_not_ad_free(self):
        self.user.ad_free_until = timezone.now() - timezone.timedelta(days=1)
        self.assertFalse(self.user.is_ad_free())

    def test_banned_ip_str(self):
        ip = BannedIps.objects.create(ip_address='192.168.0.1', reason='Spamming', related_user=self.user)
        self.assertIn('192.168.0.1', str(ip))

    def test_region_str(self):
        reg = region.objects.create(region_name='Midlands', region_code='MID')
        self.assertEqual(str(reg), "Midlands")

    def test_site_update_str(self):
        update_obj = siteUpdate.objects.create(title="New Feature", description="Description", live=True)
        self.assertEqual(str(update_obj), "New Feature - Live")

    def test_update_str(self):
        upd = update.objects.create(title="Update", body="Body text", tages="test", link="http://example.com")
        upd.readBy.add(self.user)
        self.assertEqual(str(upd), "Update")

    def test_report_str(self):
        rpt = Report.objects.create(reporter=self.user, report_type="Bug", details="Some bug", context="")
        self.assertIn("Bug report by", str(rpt))

    def test_feature_toggle_status_text(self):
        feat = featureToggle.objects.create(name="TestFeature", enabled=True)
        self.assertEqual(feat.status_text, "Enabled")

        feat.enabled = False
        feat.save()
        self.assertEqual(feat.status_text, "Disabled")

        feat.coming_soon = True
        feat.save()
        self.assertEqual(feat.status_text, "Coming Soon")

        feat.coming_soon = False
        feat.maintenance = True
        feat.save()
        self.assertEqual(feat.status_text, "Under Maintenance")
