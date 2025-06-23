from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings

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

class theme(models.Model):
    id = models.AutoField(primary_key=True)
    theme_name = models.CharField(max_length=50, blank=True, null=True)
    css = models.FileField(upload_to='themes/', help_text='Upload a CSS file. <a href="/media/themes/templateTheme.css" target="_blank">Download template</a>')
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

    def __str__(self):
        return self.ad_name

class google_ad(models.Model):
    ad_type = models.CharField(max_length=50, choices=[('article', 'Article'), ('banner', 'Banner')])
    ad_id = models.CharField(max_length=100, help_text="Google Ad ID (e.g., 6635106786)")
    ad_place_id = models.CharField(max_length=100, help_text="MBT AD Box ID (e.g., body-ad-1)")

class CustomUser(AbstractUser):
    mbt_admin_perms = models.ManyToManyField('MBTAdminPermission', related_name='users_with_perm', blank=True, help_text="Administrative permissions for MyBusTimes")
    join_date = models.DateTimeField(auto_now_add=True)
    theme = models.ForeignKey(theme, on_delete=models.SET_NULL, null=True)
    badges = models.ManyToManyField(badge, related_name='badges', blank=True)
    ticketer_code = models.CharField(max_length=50, blank=True, null=True)
    static_ticketer_code = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_active = models.DateTimeField(blank=True, null=True)
    banned = models.BooleanField(default=False)
    banned_date = models.DateTimeField(blank=True, null=True)
    banned_reason = models.TextField(blank=True, null=True)
    total_user_reports = models.PositiveIntegerField(default=0)
    ad_free_until = models.DateTimeField(null=True, blank=True)
    pfp = models.ImageField(upload_to='images/profile_pics/', default='images/default_profile_pic.png', blank=True, null=True)
    banner = models.ImageField(upload_to='images/profile_banners/', default='images/default_banner.png', blank=True, null=True)

    def is_ad_free(self):
        return self.ad_free_until and self.ad_free_until > timezone.now()
    
    def __str__(self):
        return self.username
    
User = get_user_model()

class LoginIPHashLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_hash = models.CharField(max_length=64)  # SHA-256 produces 64 hex chars
    login_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.ip_hash} - {self.login_time.strftime('%Y-%m-%d %H:%M:%S')}"

class region(models.Model):
    region_name = models.CharField(max_length=100, unique=True)
    region_code = models.CharField(max_length=3, unique=True)
    region_country = models.CharField(max_length=100, default='England')
    in_the = models.BooleanField(default=False)

    def __str__(self):
        return self.region_name

class serviceUpdate(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=50, blank=False)
    description = models.TextField(blank=False)
    live = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {'Live' if self.live else 'Not Live'}"

class featureToggle(models.Model):
    name = models.CharField(max_length=255, unique=True)
    enabled = models.BooleanField(default=True)
    maintenance = models.BooleanField(default=False)
    coming_soon = models.BooleanField(default=False)
    coming_soon_percent = models.IntegerField(default=0, validators=[MinValueValidator(1), MaxValueValidator(100)], blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {'Enabled' if self.enabled else 'Disabled'}"

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
    coming_soon = models.BooleanField(default=False)
    coming_soon_percent = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {'Enabled' if self.enabled else 'Disabled'}"

User = get_user_model()