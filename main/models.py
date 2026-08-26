from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from simple_history.models import HistoricalRecords
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
from .cloudflare_ips import *
from django.core.exceptions import ValidationError
import ipaddress
import uuid

# Create your models here.
class badge(models.Model):
    id = models.AutoField(primary_key=True)
    badge_name = models.CharField(max_length=50, blank=False)
    badge_backgroud = models.TextField(blank=False)
    badge_text_color = models.CharField(max_length=7, blank=False)
    additional_css = models.TextField(blank=True, null=True)
    
    self_asign = models.BooleanField(default=False)

    history = HistoricalRecords()

    def __str__(self):
        return self.badge_name

class MBTAdminPermission(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'MBT Admin Permission'
        verbose_name_plural = 'MBT Admin Permissions'

class MBTTeam(models.Model):
    name = models.CharField(max_length=100, unique=True)
    permissions = models.ManyToManyField(MBTAdminPermission, related_name='teams', blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.name

class theme(models.Model):
    id = models.AutoField(primary_key=True)
    theme_name = models.CharField(max_length=50, blank=True, null=True)
    light_css = models.FileField(upload_to='themes/', help_text='Upload a CSS file. <a href="https://cdn.nextstoplabs.org/mybustimes/staticfiles/themes/templateTheme.css" target="_blank">Download template</a>')
    dark_css = models.FileField(upload_to='themes/', help_text='Upload a CSS file. <a href="https://cdn.nextstoplabs.org/mybustimes/staticfiles/themes/templateTheme.css" target="_blank">Download template</a>')
    light_main_colour = models.CharField(max_length=50, blank=True)
    dark_main_colour = models.CharField(max_length=50, blank=True)
    public = models.BooleanField(default=False)  # Boolean for dark mode
    sugggested = models.BooleanField(default=False)
    weight = models.IntegerField(default=0)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.theme_name} - {'Dark' if self.public else 'Disabled'} - {self.weight}"

class ad(models.Model):
    ad_name = models.CharField(max_length=100)
    ad_img = models.ImageField(upload_to='images/')
    ad_link = models.TextField()
    ad_live = models.BooleanField(default=False)
    ad_img_overide = models.URLField(blank=True, null=True, help_text="Override image URL for the ad")

    history = HistoricalRecords()

    def __str__(self):
        return self.ad_name

class google_ad(models.Model):
    ad_type = models.CharField(max_length=50, choices=[('article', 'Article'), ('banner', 'Banner')])
    ad_id = models.CharField(max_length=100, help_text="Google Ad ID (e.g., 6635106786)")
    ad_place_id = models.CharField(max_length=100, help_text="MBT AD Box ID (e.g., body-ad-1)")

class BanType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    history = HistoricalRecords()

    def __str__(self):
        labels = {
            'wiki_edit': 'Wiki Editing',
        }
        if self.name in labels:
            return labels[self.name]
        return self.name.replace('_', ' ').title()
    
class CustomUser(AbstractUser):
    #mbt_admin_perms = models.ManyToManyField('MBTAdminPermission', related_name='users_with_perm', blank=True, help_text="Administrative permissions for MyBusTimes")
    oidc_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
    mbt_team = models.ForeignKey('MBTTeam', on_delete=models.SET_NULL, null=True, blank=True, related_name='team_members', help_text="Team the user belongs to")
    join_date = models.DateTimeField(auto_now_add=True)
    theme = models.ForeignKey(theme, on_delete=models.SET_NULL, null=True)
    dark_mode = models.BooleanField(default=False)
    badges = models.ManyToManyField(badge, related_name='badges', blank=True)
    ticketer_code = models.CharField(max_length=50, blank=True, null=True)
    static_ticketer_code = models.BooleanField(default=True)
    reg_background = models.BooleanField(default=True)
    fleet_icons = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True, db_index=True)
    last_ip = models.GenericIPAddressField(blank=True, null=True, db_index=True)
    last_active = models.DateTimeField(blank=True, null=True, db_index=True)
    banned = models.BooleanField(default=False)

    banned_from = models.ManyToManyField(BanType, blank=True, related_name='banned_users', help_text="Types of bans applied to the user")

    banned_date = models.DateTimeField(blank=True, null=True)
    banned_reason = models.TextField(blank=True, null=True)
    discord_username = models.CharField(max_length=255, blank=True, null=True)
    discord_id = models.CharField(max_length=32, unique=True, blank=True, null=True)
    discord_global_name = models.CharField(max_length=255, blank=True, null=True)
    discord_avatar = models.CharField(max_length=255, blank=True, null=True)
    total_user_reports = models.PositiveIntegerField(default=0)
    ad_free_until = models.DateTimeField(null=True, blank=True)
    pfp = models.ImageField(upload_to='images/profile_pics/', default='images/default_profile_pic.png', blank=True, null=True)
    banner = models.ImageField(upload_to='images/profile_banners/', default='images/default_banner.png', blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)

    had_pro_trial = models.BooleanField(default=False)

    PLAN_CHOICES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('pro', 'Pro'),
    ]
    
    sub_plan = models.CharField(
        max_length=10,
        choices=PLAN_CHOICES,
        default='free',
    )

    #Bus Buying stuff
    buses_brought_count = models.PositiveIntegerField(default=0)
    last_bus_purchase = models.DateTimeField(null=True, blank=True)

    admin_notes = models.TextField(blank=True, null=True, help_text="Internal notes for admins only")

    def is_ad_free(self):
        if self.ad_free_until and self.ad_free_until > timezone.now():
            return True

        from main.discord_roles import user_is_discord_booster

        return user_is_discord_booster(self)
    
    history = HistoricalRecords(excluded_fields=['last_active'])

    def __str__(self):
        return self.username

    def has_blocked(self, other_user):
        if not other_user or not other_user.pk:
            return False
        return UserBlock.objects.filter(blocker=self, blocked=other_user).exists()

    def is_blocked_by(self, other_user):
        if not other_user or not other_user.pk:
            return False
        return UserBlock.objects.filter(blocker=other_user, blocked=self).exists()

    def has_blocked_either(self, other_user):
        if not other_user or not other_user.pk:
            return False
        return UserBlock.objects.filter(
            Q(blocker=self, blocked=other_user) | Q(blocker=other_user, blocked=self)
        ).exists()
    
User = get_user_model()

class UserBlock(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocks_given')
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocks_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')
        indexes = [
            models.Index(fields=['blocker', 'blocked']),
        ]

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.blocker_id == self.blocked_id:
            raise ValidationError("You cannot block yourself.")

class ActiveSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='active_subscriptions')
    stripe_subscription_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    plan = models.CharField(max_length=100, choices=User.PLAN_CHOICES)
    is_trial = models.BooleanField(default=False)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.user.username} - {self.stripe_subscription_id}"

class StripeSubscription(models.Model):
    # When subscription starts and ends
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    # Optional product name
    product_name = models.CharField(max_length=200, null=True, blank=True)

    # Link subscription to a user in Django
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)

    # Stripe identifiers
    subscription_id = models.CharField(max_length=100, null=True)
    customer_id = models.CharField(max_length=100, null=True)

class BannedIps(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.TextField(blank=True, null=True)
    banned_at = models.DateTimeField(auto_now_add=True)
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='banned_ips'
    )

    history = HistoricalRecords()

    def clean(self):
        ip = ipaddress.ip_address(self.ip_address)

        ipv4_nets, ipv6_nets = get_cloudflare_networks()

        # Check IPv4
        if ip.version == 4:
            for net in ipv4_nets:
                if ip in net:
                    raise ValidationError("This IP belongs to Cloudflare's network and cannot be banned.")

        # Check IPv6
        if ip.version == 6:
            for net in ipv6_nets:
                if ip in net:
                    raise ValidationError("This IP belongs to Cloudflare's network and cannot be banned.")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ip_address} - {self.reason or 'No reason provided'}"


class SuspiciousSignupAlert(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='suspicious_signup_alert',
    )
    score = models.PositiveIntegerField(default=0)
    reasons = models.JSONField(default=list, blank=True)
    matching_ips = models.JSONField(default=list, blank=True)
    matching_usernames = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    webhook_sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - suspicious signup score {self.score}"
    
class region(models.Model):
    region_name = models.CharField(max_length=100, unique=True, db_index=True)
    region_code = models.CharField(max_length=3, unique=True, db_index=True)
    region_country = models.CharField(max_length=100, default='England', db_index=True)
    in_the = models.BooleanField(default=False, db_index=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.region_name

class siteUpdate(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100, blank=False)
    description = models.TextField(blank=False)
    live = models.BooleanField(default=True)
    warning = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.title} - {'Live' if self.live else 'Not Live'}"

class patchNote(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100, blank=False)
    description = models.TextField(blank=False)
    live = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.title} - {'Live' if self.live else 'Not Live'}"

class update(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=50, blank=False)
    body = models.TextField(blank=False)
    tages = models.TextField(blank=False)
    link = models.TextField(blank=True, null=True)

    readBy = models.ManyToManyField(CustomUser, blank=True, related_name="read_updates")

    history = HistoricalRecords()

    def __str__(self):
        return self.title
    
class Report(models.Model):
    BUG = 'Bug'
    USER = 'User'
    IMAGE = 'Image'

    REPORT_TYPE_CHOICES = [
        (BUG, 'Bug'),
        (USER, 'User'),
        (IMAGE, 'Image'),
    ]

    id = models.AutoField(primary_key=True)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made')
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    details = models.TextField(help_text="Describe what happened")
    context = models.TextField(blank=True, help_text="Add any links, vehicle IDs, or extra context")
    screenshot = models.ImageField(upload_to='reports/screenshots/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.report_type} report by {self.reporter.username}"

class featureToggle(models.Model):
    name = models.CharField(max_length=255, unique=True)
    enabled = models.BooleanField(default=True)
    maintenance = models.BooleanField(default=False)
    super_user_only = models.BooleanField(default=False, help_text="Only superusers can access this feature")
    coming_soon = models.BooleanField(default=False)
    coming_soon_percent = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], blank=True, null=True)

    @property
    def status_text(self):
        if self.maintenance:
            return "Under Maintenance"
        elif self.coming_soon:
            return "Coming Soon"
        elif self.enabled:
            return "Enabled"
        else:
            return "Disabled"

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name} - {'Enabled' if self.enabled else 'Disabled'}"

class ImportJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='pending')  # pending, running, done, error
    progress = models.IntegerField(default=0)  # 0-100%
    message = models.TextField(blank=True, null=True)  # Current step message
    username_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

class UserKeys(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_keys")
    session_key = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.user.username} - {self.session_key}"


class CommunityImages(models.Model):
    id = models.AutoField(primary_key=True)
    image = models.ImageField(upload_to='community_images/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_images')
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"Image {self.id} uploaded by {self.uploaded_by.username}"


class DeviceBan(models.Model):
    fingerprint = models.CharField(max_length=128, unique=True)
    reason = models.TextField(blank=True, null=True)
    banned_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_bans'
    )

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.fingerprint} - {'Active' if self.active else 'Inactive'}"

class Device(models.Model):
    fingerprint = models.CharField(max_length=128, unique=True, db_index=True)
    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True, db_index=True)
    last_ip = models.GenericIPAddressField(blank=True, null=True, db_index=True)
    last_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices', db_index=True)
    user_agent = models.TextField(blank=True, null=True, db_index=True)
    seen_count = models.PositiveIntegerField(default=0, db_index=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.fingerprint


class DeviceUsage(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='usages', db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_usages', db_index=True)
    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True, db_index=True)
    usage_count = models.PositiveIntegerField(default=0, db_index=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ('device', 'user')

    def __str__(self):
        return f"{self.device.fingerprint} - {self.user.username}"

User = get_user_model()
