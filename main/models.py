from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
import uuid

# Create your models here.
class badge(models.Model):
    id = models.AutoField(primary_key=True)
    badge_name = models.CharField(max_length=50, blank=False)
    badge_backgroud = models.TextField(blank=False)
    badge_text_color = models.CharField(max_length=7, blank=False)
    additional_css = models.TextField(blank=True, null=True)
    
    self_asign = models.BooleanField(default=False)

    def __str__(self):
        return self.badge_name

class MBTAdminPermission(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'MBT Admin Permission'
        verbose_name_plural = 'MBT Admin Permissions'

class MBTTeam(models.Model):
    name = models.CharField(max_length=100, unique=True)
    permissions = models.ManyToManyField(MBTAdminPermission, related_name='teams', blank=True)

    def __str__(self):
        return self.name

class theme(models.Model):
    id = models.AutoField(primary_key=True)
    theme_name = models.CharField(max_length=50, blank=True, null=True)
    css = models.FileField(upload_to='themes/', help_text='Upload a CSS file. <a href="/static/themes/templateTheme.css" target="_blank">Download template</a>')
    main_colour = models.CharField(max_length=50, blank=True)
    dark_theme = models.BooleanField(default=False)  # Boolean for dark mode
    weight = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.theme_name} - {'Dark' if self.dark_theme else 'Light'} - {self.weight}"

class ad(models.Model):
    ad_name = models.CharField(max_length=100)
    ad_img = models.ImageField(upload_to='images/')
    ad_link = models.TextField()
    ad_live = models.BooleanField(default=False)
    ad_img_overide = models.URLField(blank=True, null=True, help_text="Override image URL for the ad")

    def __str__(self):
        return self.ad_name

class google_ad(models.Model):
    ad_type = models.CharField(max_length=50, choices=[('article', 'Article'), ('banner', 'Banner')])
    ad_id = models.CharField(max_length=100, help_text="Google Ad ID (e.g., 6635106786)")
    ad_place_id = models.CharField(max_length=100, help_text="MBT AD Box ID (e.g., body-ad-1)")

class CustomUser(AbstractUser):
    #mbt_admin_perms = models.ManyToManyField('MBTAdminPermission', related_name='users_with_perm', blank=True, help_text="Administrative permissions for MyBusTimes")
    mbt_team = models.ForeignKey('MBTTeam', on_delete=models.SET_NULL, null=True, blank=True, related_name='team_members', help_text="Team the user belongs to")
    join_date = models.DateTimeField(auto_now_add=True)
    theme = models.ForeignKey(theme, on_delete=models.SET_NULL, null=True)
    badges = models.ManyToManyField(badge, related_name='badges', blank=True)
    ticketer_code = models.CharField(max_length=50, blank=True, null=True)
    static_ticketer_code = models.BooleanField(default=True)
    reg_background = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_active = models.DateTimeField(blank=True, null=True)
    banned = models.BooleanField(default=False)
    banned_date = models.DateTimeField(blank=True, null=True)
    banned_reason = models.TextField(blank=True, null=True)
    discord_username = models.CharField(max_length=255, blank=True, null=True)
    total_user_reports = models.PositiveIntegerField(default=0)
    ad_free_until = models.DateTimeField(null=True, blank=True)
    pfp = models.ImageField(upload_to='images/profile_pics/', default='images/default_profile_pic.png', blank=True, null=True)
    banner = models.ImageField(upload_to='images/profile_banners/', default='images/default_banner.png', blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)

    #Bus Buying stuff
    buses_brought_count = models.PositiveIntegerField(default=0)
    last_bus_purchase = models.DateTimeField(null=True, blank=True)

    admin_notes = models.TextField(blank=True, null=True, help_text="Internal notes for admins only")

    def is_ad_free(self):
        return self.ad_free_until and self.ad_free_until > timezone.now()
    
    def __str__(self):
        return self.username
    
User = get_user_model()

class BannedIps(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.TextField(blank=True, null=True)
    banned_at = models.DateTimeField(auto_now_add=True)
    related_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='banned_ips')
    
    def __str__(self):
        return f"{self.ip_address} - {self.reason or 'No reason provided'}"
    
class region(models.Model):
    region_name = models.CharField(max_length=100, unique=True)
    region_code = models.CharField(max_length=3, unique=True)
    region_country = models.CharField(max_length=100, default='England')
    in_the = models.BooleanField(default=False)

    def __str__(self):
        return self.region_name

class siteUpdate(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100, blank=False)
    description = models.TextField(blank=False)
    live = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {'Live' if self.live else 'Not Live'}"
    
class patchNote(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100, blank=False)
    description = models.TextField(blank=False)
    live = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {'Live' if self.live else 'Not Live'}"

class update(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=50, blank=False)
    body = models.TextField(blank=False)
    tages = models.TextField(blank=False)
    link = models.TextField(blank=True, null=True)

    readBy = models.ManyToManyField(CustomUser, blank=True, related_name="read_updates")

    def __str__(self):
        return self.title
    
class Report(models.Model):
    BUG = 'Bug'
    USER = 'User'

    REPORT_TYPE_CHOICES = [
        (BUG, 'Bug'),
        (USER, 'User'),
    ]

    id = models.AutoField(primary_key=True)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made')
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    details = models.TextField(help_text="Describe what happened")
    context = models.TextField(blank=True, help_text="Add any links, vehicle IDs, or extra context")
    screenshot = models.ImageField(upload_to='reports/screenshots/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

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

class UserKeys(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_keys")
    session_key = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.session_key}"


User = get_user_model()