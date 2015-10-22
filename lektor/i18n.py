# XXX: this is just a shitty temporary thing
import os


KNOWN_LANGUAGES = ['en', 'de']


def get_default_lang():
    for key in 'LANGUAGE', 'LC_ALL', 'LC_CTYPE', 'LANG':
        value = os.environ.get(key)
        if not value:
            continue
        lang = value.split('_')[0].lower()
        if is_valid_language(lang):
            return lang
    return 'en'


def is_valid_language(lang):
    return lang in KNOWN_LANGUAGES
