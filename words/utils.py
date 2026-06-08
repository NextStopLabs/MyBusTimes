import re

from words.models import bannedWord, whitelistedWord


def banned_words_in_text(text, scope=bannedWord.SEARCH_SCOPE):
    if scope != 'all' and not bannedWord.valid_scope(scope):
        raise ValueError(f'Invalid banned word scope: {scope}')

    words = [word.lower() for word in re.split(r'\s+', text or '') if word]
    if not words:
        return []

    whitelisted_set = set(word.lower() for word in whitelistedWord.objects.values_list('word', flat=True))

    banned_words = bannedWord.objects.all()
    if scope != 'all':
        banned_words = banned_words.filter(**{bannedWord.SCOPE_FIELD_MAP[scope]: True})

    banned_set = set(word.lower() for word in banned_words.values_list('word', flat=True))

    return [
        word
        for word in words
        if word in banned_set and word not in whitelisted_set
    ]


def contains_banned_word(text, scope=bannedWord.SEARCH_SCOPE):
    return bool(banned_words_in_text(text, scope))
