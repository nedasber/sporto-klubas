from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from .models import Training, MembershipPlan


# Treniruočių tipų sąrašas – galima lengvai papildyti
TRAINING_TYPE_CHOICES = [
    ("", _("— Pasirinkite tipą —")),
    ("Joga", _("Joga")),
    ("CrossFit", _("CrossFit")),
    ("Spin / Dviratis", _("Spin / Dviratis")),
    ("Boksas", _("Boksas")),
    ("Svorių salė", _("Svorių salė")),
    ("Pilatesas", _("Pilatesas")),
    ("Zumba", _("Zumba")),
    ("HIIT", _("HIIT")),
    ("Bėgimas", _("Bėgimas")),
    ("Plaukimas", _("Plaukimas")),
    ("Stretching", _("Stretching")),
    ("Kita", _("Kita")),
]


# ============================================================
# TRENIRUOTĖS LIMITAI
# ============================================================
MIN_DURATION = 15      # min
MAX_DURATION = 240     # 4 val.
MIN_CAPACITY = 1
MAX_CAPACITY = 20

# Maks. įkeliamo paveikslėlio dydis (MB)
MAX_IMAGE_SIZE_MB = 5


class TrainingForm(forms.ModelForm):
    title = forms.ChoiceField(
        choices=TRAINING_TYPE_CHOICES,
        label=_("Treniruotės tipas"),
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}),
        error_messages={
            "required": _("Pasirinkite treniruotės tipą."),
        },
    )

    starts_at = forms.DateTimeField(
        label=_("Pradžios data ir laikas"),
        widget=forms.DateTimeInput(attrs={
            "type": "text",
            "class": "form-control form-control-lg flatpickr-input",
            "placeholder": _("Spragtelėkite, kad pasirinktumėte datą..."),
            "autocomplete": "off",
        }),
        error_messages={
            "required": _("Įveskite pradžios datą ir laiką."),
            "invalid": _("Įveskite teisingą datą ir laiką."),
        },
    )

    duration_minutes = forms.IntegerField(
        label=_("Trukmė (minutėmis)"),
        widget=forms.NumberInput(attrs={
            "class": "form-control form-control-lg",
            "min": MIN_DURATION,
            "max": MAX_DURATION,
            "step": 5,
        }),
        error_messages={
            "required": _("Įveskite treniruotės trukmę."),
            "invalid": _("Trukmė turi būti skaičius."),
        },
    )

    capacity = forms.IntegerField(
        label=_("Maksimalus dalyvių skaičius"),
        widget=forms.NumberInput(attrs={
            "class": "form-control form-control-lg",
            "min": MIN_CAPACITY,
            "max": MAX_CAPACITY,
        }),
        error_messages={
            "required": _("Įveskite maksimalų dalyvių skaičių."),
            "invalid": _("Dalyvių skaičius turi būti skaičius."),
        },
    )

    description = forms.CharField(
        label=_("Aprašymas"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    # Paveikslėlio failas – įkeliamas iš kompiuterio
    image = forms.ImageField(
        label=_("Įkeltas paveikslėlis"),
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": "image/jpeg,image/png,image/webp",
        }),
        error_messages={
            "invalid_image": _("Įkeltas failas nėra paveikslėlis arba yra sugadintas."),
        },
    )

    # URL laukas iš galerijos – pildomas automatiškai JS, paslėptas vartotojui
    image_url = forms.URLField(
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Training
        fields = [
            "title",
            "starts_at",
            "duration_minutes",
            "capacity",
            "description",
            "image",
            "image_url",
        ]

    # ----- VALIDACIJOS -----

    def clean_starts_at(self):
        starts_at = self.cleaned_data.get("starts_at")
        if not starts_at:
            raise forms.ValidationError(_("Įveskite pradžios datą ir laiką."))

        # Jei redaguojama esama treniruotė ir laikas nepasikeitė - leidžiame
        if self.instance and self.instance.pk and self.instance.starts_at == starts_at:
            return starts_at

        if starts_at < timezone.now():
            raise forms.ValidationError(_("Treniruotės negalima kurti praeityje. Pasirinkite būsimą datą ir laiką."))
        return starts_at

    def clean_duration_minutes(self):
        duration = self.cleaned_data.get("duration_minutes")
        if duration is None:
            raise forms.ValidationError(_("Įveskite treniruotės trukmę."))
        if duration < MIN_DURATION:
            raise forms.ValidationError(
                _("Treniruotė turi trukti bent %(min)d minutes.") % {"min": MIN_DURATION}
            )
        if duration > MAX_DURATION:
            raise forms.ValidationError(
                _("Treniruotė negali būti ilgesnė nei %(max)d minutės (%(hours)d valandos).") % {
                    "max": MAX_DURATION,
                    "hours": MAX_DURATION // 60,
                }
            )
        return duration

    def clean_capacity(self):
        capacity = self.cleaned_data.get("capacity")
        if capacity is None:
            raise forms.ValidationError(_("Įveskite maksimalų dalyvių skaičių."))
        if capacity < MIN_CAPACITY:
            raise forms.ValidationError(
                _("Mažiausias dalyvių skaičius – %(min)d.") % {"min": MIN_CAPACITY}
            )
        if capacity > MAX_CAPACITY:
            raise forms.ValidationError(
                _("Didžiausias dalyvių skaičius – %(max)d.") % {"max": MAX_CAPACITY}
            )
        return capacity

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image
        # Patikrinam dydį
        max_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024
        if image.size > max_bytes:
            raise forms.ValidationError(
                _("Paveikslėlis per didelis. Maksimalus dydis – %(max)d MB.") % {"max": MAX_IMAGE_SIZE_MB}
            )
        return image

    def clean(self):
        """Jei įkeltas naujas failas, panaikinam image_url, kad nesimaišytų."""
        cleaned = super().clean()
        if cleaned.get("image"):
            cleaned["image_url"] = ""
        return cleaned


# ============================================================
# ABONEMENTŲ PIRKIMAS
# ============================================================
phone_validator = RegexValidator(
    regex=r"^\+?\d{7,15}$",
    message=_("Telefonas turi būti tik skaičiai (galima su +), 7–15 simbolių.")
)


class MembershipPurchaseForm(forms.Form):
    full_name = forms.CharField(
        label=_("Vardas, pavardė"),
        max_length=120,
        error_messages={
            "required": _("Įveskite vardą ir pavardę."),
        },
    )
    phone = forms.CharField(
        label=_("Telefono numeris"),
        max_length=20,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            "type": "tel",
            "inputmode": "numeric",
            "placeholder": "+3706..."
        }),
        error_messages={
            "required": _("Įveskite telefono numerį."),
        },
    )
