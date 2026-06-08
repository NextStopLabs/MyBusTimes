from django.test import TestCase
from django.test import RequestFactory
import json

from words.admin import BannedWordAdminForm
from words.models import bannedWord
from words.models import whitelistedWord
from words.utils import banned_words_in_text
from words.views import check_string_view


class BannedWordScopeTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def post_check_string(self, query, scope=None):
        data = {'query': query}
        if scope:
            data['scope'] = scope
        request = self.factory.post('/api/check-string/', data)
        response = check_string_view(request)
        return json.loads(response.content)

    def test_check_string_uses_requested_scope(self):
        bannedWord.objects.create(
            word='blockedoperator',
            ban_search=False,
            ban_operator_name=True,
            ban_group_name=False,
            ban_username=False,
        )

        search_result = self.post_check_string('blockedoperator', 'search')
        operator_result = self.post_check_string('blockedoperator', 'operator_name')

        self.assertEqual(search_result['results'][0]['status'], 'ok')
        self.assertEqual(operator_result['results'][0]['status'], 'banned')

    def test_check_string_defaults_to_search_scope(self):
        bannedWord.objects.create(
            word='blockedsearch',
            ban_search=True,
            ban_operator_name=False,
            ban_group_name=False,
            ban_username=False,
        )

        result = self.post_check_string('blockedsearch')

        self.assertEqual(result['scope'], bannedWord.SEARCH_SCOPE)
        self.assertEqual(result['results'][0]['status'], 'banned')

    def test_admin_select_all_enables_every_scope(self):
        form = BannedWordAdminForm(data={
            'word': 'blockedall',
            'insta_ban': '',
            'ban_all': 'on',
            'ban_search': '',
            'ban_operator_name': '',
            'ban_group_name': '',
            'ban_username': '',
        })

        self.assertTrue(form.is_valid())
        word = form.save()

        self.assertTrue(word.ban_search)
        self.assertTrue(word.ban_operator_name)
        self.assertTrue(word.ban_group_name)
        self.assertTrue(word.ban_username)

    def test_banned_words_in_text_respects_scope(self):
        bannedWord.objects.create(
            word='blockedname',
            ban_search=False,
            ban_operator_name=True,
            ban_group_name=False,
            ban_username=False,
        )

        self.assertEqual(
            banned_words_in_text('BlockedName Buses', bannedWord.OPERATOR_NAME_SCOPE),
            ['blockedname'],
        )
        self.assertEqual(
            banned_words_in_text('BlockedName Buses', bannedWord.GROUP_NAME_SCOPE),
            [],
        )

    def test_banned_words_in_text_respects_whitelist(self):
        bannedWord.objects.create(word='allowedword', ban_operator_name=True)
        whitelistedWord.objects.create(word='allowedword')

        self.assertEqual(
            banned_words_in_text('allowedword Buses', bannedWord.OPERATOR_NAME_SCOPE),
            [],
        )
