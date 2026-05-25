"""
Šablono filtrai ir tagai sporto klubo aplikacijai.
"""
from django import template
from django.utils.translation import gettext as _

register = template.Library()


@register.filter(name='translate')
def translate(value):
    """
    Verčia DB tekstą per Django i18n sistemą.
    Naudojimas šablone: {{ plan.name|translate }}

    Jeigu vertimo nėra, grąžina originalą.
    """
    if value is None:
        return ""
    return _(str(value))
