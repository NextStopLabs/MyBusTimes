from django.db import models
from simple_history.models import HistoricalRecords

class bannedWord(models.Model):
    word = models.CharField(max_length=100, unique=True)
    insta_ban = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return self.word

class whitelistedWord(models.Model):
    word = models.CharField(max_length=100, unique=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.word