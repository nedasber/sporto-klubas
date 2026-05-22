"""
Template tag'ai duomenų bazės tekstams versti.
Naudojimas šablone: {{ achievement.name|trans_db }}
"""
from django import template
from django.utils.translation import gettext

register = template.Library()


@register.filter
def trans_db(value):
    """Bando išversti DB lauką per gettext. Jei vertimo nėra – grąžina originalą."""
    if not value:
        return value
    return gettext(value)
