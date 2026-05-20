LANGUAGES_DATA = {
    'uz': {
        'name': "O'zbek",
        'native': "O'zbek",
        'flag': '🇺🇿',
        'code': 'uz',
    },
    'ru': {
        'name': 'Русский',
        'native': 'Русский',
        'flag': '🇷🇺',
        'code': 'ru',
    },
    'en': {
        'name': 'English',
        'native': 'English',
        'flag': '🇬🇧',
        'code': 'en',
    },
}

def get_language_name(code):
    return LANGUAGES_DATA.get(code, LANGUAGES_DATA['uz'])['name']

def get_available_languages():
    return list(LANGUAGES_DATA.values())
