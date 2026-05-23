"""
Middleware, kuris priverstinai įjungia lietuvių kalbą Django admin'e,
nepriklausomai nuo naršyklės Accept-Language antraštės.
"""
from django.utils import translation


class AdminLanguageMiddleware:
    """Visada nustato LT kalbą /admin/ puslapiuose."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            translation.activate("lt")
            request.LANGUAGE_CODE = "lt"
        response = self.get_response(request)
        return response
