from django.db import models
from simple_history.models import HistoricalRecords

class CustomModel(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name