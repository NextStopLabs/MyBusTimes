from django.db import models

# Create your models here.
class Link(models.Model):
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField()
    active = models.BooleanField(default=True)
    clicks = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name