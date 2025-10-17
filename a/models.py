from django.db import models
from simple_history.models import HistoricalRecords
from main.models import CustomUser as User

# Create your models here.
class Link(models.Model):
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField()
    active = models.BooleanField(default=True)
    clicks = models.PositiveIntegerField(default=0)

    history = HistoricalRecords()

    def __str__(self):
        return self.name

class AffiliateLink(models.Model):
    tag = models.CharField(max_length=50)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    clicks = models.PositiveIntegerField(default=0)
    signups_from_clicks = models.PositiveIntegerField(default=0)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.tag} -> {self.clicks}"