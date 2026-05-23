from django import forms
from django.utils import timezone
from django.core.validators import RegexValidator
from .models import Training, MembershipPlan


# Treniruočių tipų sąrašas – galima lengvai papildyti
TRAINING_TYPE_CHOICES = [
    ("", "— Pasirinkite tipą —"),
    ("Joga", "Joga"),
    ("CrossFit", "CrossFit"),
    ("Spin / Dviratis", "Spin / Dviratis"),
    ("Boksas", "Boksas"),
    ("Svorių salė", "Svorių salė"),
    ("Pilatesas", "Pilatesas"),
    ("Zumba", "Zumba"),
    ("HIIT", "HIIT"),
    ("Bėgimas", "Bėgimas"),
    ("Plaukimas", "Plaukimas"),
    ("Stretching", "Stretching"),
    ("Kita", "Kita"),
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
        label="Treniruotės tipas",
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}),
        error_messages={
            "required": "Pasirinkite treniruotės tipą.",
        },
    )

    starts_at = forms.DateTimeField(
        label="Pradžios data ir laikas",
        widget=forms.DateTimeInput(attrs={
            "type": "text",
            "class": "form-control form-control-lg flatpickr-input",
            "placeholder": "Spragtelėkite, kad pasirinktumėte datą...",
            "autocomplete": "off",
        }),
        error_messages={
            "required": "Įveskite pradžios datą ir laiką.",
            "invalid": "Įveskite teisingą datą ir laiką.",
        },
    )

    duration_minutes = forms.IntegerField(
        label="Trukmė (minutėmis)",
        widget=forms.NumberInput(attrs={
            "class": "form-control form-control-lg",
            "min": MIN_DURATION,
            "max": MAX_DURATION,
            "step": 5,
        }),
        error_messages={
            "required": "Įveskite treniruotės trukmę.",
            "invalid": "Trukmė turi būti skaičius.",
        },
    )

    capacity = forms.IntegerField(
        label="Maksimalus dalyvių skaičius",
        widget=forms.NumberInput(attrs={
            "class": "form-control form-control-lg",
            "min": MIN_CAPACITY,
            "max": MAX_CAPACITY,
        }),
        error_messages={
            "required": "Įveskite maksimalų dalyvių skaičių.",
            "invalid": "Dalyvių skaičius turi būti skaičius.",
        },
    )

    description = forms.CharField(
        label="Aprašymas",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    # Paveikslėlio failas – įkeliamas iš kompiuterio
    image = forms.ImageField(
        label="Įkeltas paveikslėlis",
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": "image/jpeg,image/png,image/webp",
        }),
        error_messages={
            "invalid_image": "Įkeltas failas nėra paveikslėlis arba yra sugadintas.",
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
            raise forms.ValidationError("Įveskite pradžios datą ir laiką.")

        # Jei redaguojama esama treniruotė ir laikas nepasikeitė - leidžiame
        if self.instance and self.instance.pk and self.instance.starts_at == starts_at:
            return starts_at

        if starts_at < timezone.now():
            raise forms.ValidationError("Treniruotės negalima kurti praeityje. Pasirinkite būsimą datą ir laiką.")
        return starts_at

    def clean_duration_minutes(self):
        duration = self.cleaned_data.get("duration_minutes")
        if duration is None:
            raise forms.ValidationError("Įveskite treniruotės trukmę.")
        if duration < MIN_DURATION:
            raise forms.ValidationError(f"Treniruotė turi trukti bent {MIN_DURATION} minutes.")
        if duration > MAX_DURATION:
            raise forms.ValidationError(
                f"Treniruotė negali būti ilgesnė nei {MAX_DURATION} minutės ({MAX_DURATION // 60} valandos)."
            )
        return duration

    def clean_capacity(self):
        capacity = self.cleaned_data.get("capacity")
        if capacity is None:
            raise forms.ValidationError("Įveskite maksimalų dalyvių skaičių.")
        if capacity < MIN_CAPACITY:
            raise forms.ValidationError(f"Mažiausias dalyvių skaičius – {MIN_CAPACITY}.")
        if capacity > MAX_CAPACITY:
            raise forms.ValidationError(f"Didžiausias dalyvių skaičius – {MAX_CAPACITY}.")
        return capacity

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image
        # Patikrinam dydį
        max_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024
        if image.size > max_bytes:
            raise forms.ValidationError(
                f"Paveikslėlis per didelis. Maksimalus dydis – {MAX_IMAGE_SIZE_MB} MB."
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
    message="Telefonas turi būti tik skaičiai (galima su +), 7–15 simbolių."
)


class MembershipPurchaseForm(forms.Form):
    full_name = forms.CharField(
        label="Vardas, pavardė",
        max_length=120,
        error_messages={
            "required": "Įveskite vardą ir pavardę.",
        },
    )
    phone = forms.CharField(
        label="Telefono numeris",
        max_length=20,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            "type": "tel",
            "inputmode": "numeric",
            "placeholder": "+3706..."
        }),
        error_messages={
            "required": "Įveskite telefono numerį.",
        },
    )
