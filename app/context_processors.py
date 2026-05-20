from .translations import LANGUAGES_DATA
from django.conf import settings

LANG = {}

def load_translations():
    for code in LANGUAGES_DATA:
        try:
            module = __import__(f'app.lang_{code}', fromlist=['T'])
            LANG[code] = getattr(module, 'T')
        except (ImportError, AttributeError):
            LANG[code] = {}

load_translations()

def language_processor(request):
    lang_code = request.session.get('lang', 'uz')
    if lang_code not in LANG:
        lang_code = 'uz'
    request.lang_code = lang_code
    return {
        't': LANG.get(lang_code, {}),
        'current_lang': lang_code,
        'languages': list(LANGUAGES_DATA.values()),
    }
