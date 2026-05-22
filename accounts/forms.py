from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _

User = get_user_model()

EMAIL_INVALID_JS = (
    "this.setCustomValidity("
    "'Įveskite teisingą el. pašto adresą (pvz. vardas@pastas.lt).'"
    ")"
)
REQUIRED_INVALID_JS = "this.setCustomValidity('Šis laukas privalomas.')"
CLEAR_VALIDITY_JS = "this.setCustomValidity('')"


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label=_("El. paštas"),
        help_text=_("Į šį adresą bus išsiųstas patvirtinimo laiškas."),
        error_messages={
            "invalid": _("Įveskite teisingą el. pašto adresą."),
            "required": _("Įveskite el. pašto adresą."),
        },
        widget=forms.EmailInput(attrs={
            "oninvalid": EMAIL_INVALID_JS,
            "oninput": CLEAR_VALIDITY_JS,
        }),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise forms.ValidationError(_("Įveskite el. pašto adresą."))
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Šis el. pašto adresas jau yra užregistruotas."))
        return email

    username = forms.CharField(
        label=_("Vartotojo vardas"),
        max_length=150,
        help_text=_("Privaloma. Iki 150 simbolių. Tik raidės, skaitmenys ir @/./+/-/_."),
        error_messages={
            "required": _("Įveskite vartotojo vardą."),
            "unique": _("Toks vartotojo vardas jau egzistuoja."),
            "max_length": _("Vartotojo vardas negali būti ilgesnis nei 150 simbolių."),
            "invalid": _("Vartotojo varde gali būti tik raidės, skaitmenys ir simboliai @/./+/-/_."),
        },
        widget=forms.TextInput(attrs={
            "oninvalid": REQUIRED_INVALID_JS,
            "oninput": CLEAR_VALIDITY_JS,
        }),
    )

    password1 = forms.CharField(
        label=_("Slaptažodis"),
        widget=forms.PasswordInput(attrs={
            "oninvalid": REQUIRED_INVALID_JS,
            "oninput": CLEAR_VALIDITY_JS,
        }),
        help_text=_(
            "Slaptažodis turi būti bent 8 simbolių ilgio. "
            "Negali būti panašus į kitus jūsų asmeninius duomenis. "
            "Negali būti dažnai naudojamas slaptažodis. "
            "Negali būti sudarytas vien tik iš skaitmenų."
        ),
        error_messages={
            "required": _("Įveskite slaptažodį."),
        },
    )

    password2 = forms.CharField(
        label=_("Pakartokite slaptažodį"),
        widget=forms.PasswordInput(attrs={
            "oninvalid": REQUIRED_INVALID_JS,
            "oninput": CLEAR_VALIDITY_JS,
        }),
        help_text=_("Pakartokite tą patį slaptažodį patikrinimui."),
        error_messages={
            "required": _("Pakartokite slaptažodį."),
        },
    )

    error_messages = {
        "password_mismatch": _("Slaptažodžiai nesutampa."),
    }

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Slaptažodžiai nesutampa."))
        return password2


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Vartotojo vardas"),
        error_messages={
            "required": _("Įveskite vartotojo vardą."),
        },
        widget=forms.TextInput(attrs={
            "oninvalid": REQUIRED_INVALID_JS,
            "oninput": CLEAR_VALIDITY_JS,
        }),
    )

    password = forms.CharField(
        label=_("Slaptažodis"),
        widget=forms.PasswordInput(attrs={
            "oninvalid": REQUIRED_INVALID_JS,
            "oninput": CLEAR_VALIDITY_JS,
        }),
        error_messages={
            "required": _("Įveskite slaptažodį."),
        },
    )

    error_messages = {
        "invalid_login": _("Neteisingas vartotojo vardas arba slaptažodis. "
                          "Patikrinkite ar teisingai įvedėte (atkreipkite dėmesį, kad svarbu didžiosios/mažosios raidės)."),
        "inactive": _("Ši paskyra yra neaktyvi."),
    }
