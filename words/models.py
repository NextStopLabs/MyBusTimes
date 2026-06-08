from django.db import models
from simple_history.models import HistoricalRecords

class bannedWord(models.Model):
    SEARCH_SCOPE = 'search'
    OPERATOR_NAME_SCOPE = 'operator_name'
    GROUP_NAME_SCOPE = 'group_name'
    USERNAME_SCOPE = 'username'

    SCOPE_FIELD_MAP = {
        SEARCH_SCOPE: 'ban_search',
        OPERATOR_NAME_SCOPE: 'ban_operator_name',
        GROUP_NAME_SCOPE: 'ban_group_name',
        USERNAME_SCOPE: 'ban_username',
    }

    SCOPE_CHOICES = (
        (SEARCH_SCOPE, 'Search ban'),
        (OPERATOR_NAME_SCOPE, 'Operator name ban'),
        (GROUP_NAME_SCOPE, 'Group name ban'),
        (USERNAME_SCOPE, 'Username ban'),
    )

    word = models.CharField(max_length=100, unique=True)
    insta_ban = models.BooleanField(default=False)
    ban_search = models.BooleanField(default=True, verbose_name='Search ban')
    ban_operator_name = models.BooleanField(default=True, verbose_name='Operator name ban')
    ban_group_name = models.BooleanField(default=True, verbose_name='Group name ban')
    ban_username = models.BooleanField(default=True, verbose_name='Username ban')
    history = HistoricalRecords()

    def __str__(self):
        return self.word

    @classmethod
    def valid_scope(cls, scope):
        return scope in cls.SCOPE_FIELD_MAP

class whitelistedWord(models.Model):
    word = models.CharField(max_length=100, unique=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.word
