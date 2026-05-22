"""
Pasirinktiniai slaptažodžio validatoriai su LT/EN pranešimais.
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import (
    MinimumLengthValidator,
    UserAttributeSimilarityValidator,
    CommonPasswordValidator,
    NumericPasswordValidator,
)


class LTMinimumLengthValidator(MinimumLengthValidator):
    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("Slaptažodis per trumpas. Jis turi būti bent %(min_length)d simbolių ilgio.") % {"min_length": self.min_length},
                code="password_too_short",
                params={"min_length": self.min_length},
            )

    def get_help_text(self):
        return _("Slaptažodis turi būti bent %(min_length)d simbolių ilgio.") % {"min_length": self.min_length}


class LTUserAttributeSimilarityValidator(UserAttributeSimilarityValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                _("Slaptažodis pernelyg panašus į jūsų asmeninius duomenis (vartotojo vardą, el. paštą ir pan.)."),
                code="password_too_similar",
            )

    def get_help_text(self):
        return _("Slaptažodis negali būti panašus į kitus jūsų asmeninius duomenis.")


class LTCommonPasswordValidator(CommonPasswordValidator):
    def validate(self, password, user=None):
        if password.lower().strip() in self.passwords:
            raise ValidationError(
                _("Šis slaptažodis pernelyg dažnai naudojamas. Pasirinkite saugesnį."),
                code="password_too_common",
            )

    def get_help_text(self):
        return _("Slaptažodis negali būti dažnai naudojamas (pvz. 'password', '12345678').")


class LTNumericPasswordValidator(NumericPasswordValidator):
    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError(
                _("Slaptažodis negali būti sudarytas vien tik iš skaitmenų."),
                code="password_entirely_numeric",
            )

    def get_help_text(self):
        return _("Slaptažodis negali būti sudarytas vien tik iš skaitmenų.")
