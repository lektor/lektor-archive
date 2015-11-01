# XXX: this is just a shitty temporary thing
import os
import json


translations_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'translations')
KNOWN_LANGUAGES = list(x[:-5] for x in os.listdir(translations_path)
                       if x.endswith('.json'))


translations = {}
for _lang in KNOWN_LANGUAGES:
    with open(os.path.join(translations_path, _lang + '.json')) as f:
        translations[_lang] = json.load(f)


def get_translations(language):
    return translations.get(language)


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


def load_i18n_block(key):
    rv = {}
    for lang in KNOWN_LANGUAGES:
        val = translations.get(lang, {}).get(key)
        if val is not None:
            rv[lang] = val
    return rv


def get_i18n_block(inifile_or_dict, key, default_lang='en'):
    rv = {}
    for k, v in inifile_or_dict.iteritems():
        if k == key:
            rv[default_lang] = v
        elif k.startswith(key + '['):
            rv[k[len(key) + 1:-1]] = v
    return rv
