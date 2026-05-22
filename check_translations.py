"""
Debug skriptas - paleisk:
python check_translations.py
"""
import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils.translation import gettext, activate
from django.conf import settings

print("=" * 60)
print("DJANGO TRANSLATIONS DEBUG")
print("=" * 60)
print("LANGUAGE_CODE:", settings.LANGUAGE_CODE)
print("LANGUAGES:", settings.LANGUAGES)
print("LOCALE_PATHS:", [str(p) for p in settings.LOCALE_PATHS])
print("USE_I18N:", settings.USE_I18N)

for path in settings.LOCALE_PATHS:
    print("\nLOCALE_PATH exists:", os.path.exists(str(path)))
    en_mo = os.path.join(str(path), 'en', 'LC_MESSAGES', 'django.mo')
    print("  django.mo exists:", os.path.exists(en_mo))
    if os.path.exists(en_mo):
        print("  django.mo size:", os.path.getsize(en_mo), "bytes")

print("\n--- Testuojam vertimus ---")
activate('en')
tests = [
    "Sporto klubas",
    "Narys",
    "Pirmas zingsnis",
    "Pirmas \u017eingsnis",  # su tikra LT raide
    "1 men. neribotas",
    "Vienkartinis apsilankymas",
]
for text in tests:
    translated = gettext(text)
    status = "[OK]" if translated != text else "[NO]"
    # Saugus print - pakeičia simbolius kurių konsolė nepalaiko
    safe_text = text.encode('ascii', 'replace').decode('ascii')
    safe_trans = translated.encode('ascii', 'replace').decode('ascii')
    print(status, "'" + safe_text + "' -> '" + safe_trans + "'")
