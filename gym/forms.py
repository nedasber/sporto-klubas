from django import forms
from .models import Training
from django.utils import timezone
from .models import MembershipPlan
from django.core.validators import RegexValidator


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


class TrainingForm(forms.ModelForm):
    # Pakeičiam "title" lauką į pasirinkimo sąrašą
    title = forms.ChoiceField(
        choices=TRAINING_TYPE_CHOICES,
        label="Treniruotės tipas",
        widget=forms.Select(attrs={"class": "form-select form-select-lg"})
    )

    class Meta:
        model = Training
        fields = [
            "title",
            "starts_at",
            "duration_minutes",
            "capacity",
            "description",
            "image_url",
        ]

        labels = {
            "starts_at": "Pradžios data ir laikas",
            "duration_minutes": "Trukmė (minutėmis)",
            "capacity": "Maksimalus dalyvių skaičius",
            "description": "Aprašymas",
            "image_url": "Paveikslėlio nuoroda",
        }

        help_texts = {
            "image_url": "Pasirinkite paveikslėlį iš galerijos arba įklijuokite savo URL",
        }

        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control form-control-lg"}
            ),
            "duration_minutes": forms.NumberInput(attrs={"class": "form-control form-control-lg", "min": 1}),
            "capacity": forms.NumberInput(attrs={"class": "form-control form-control-lg", "min": 1}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "image_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
        }


phone_validator = RegexValidator(
    regex=r"^\+?\d{7,15}$",
    message="Telefonas turi būti tik skaičiai (galima su +), 7–15 simbolių."
)


class MembershipPurchaseForm(forms.Form):
    full_name = forms.CharField(label="Vardas, pavardė", max_length=120)
    phone = forms.CharField(
        label="Telefono numeris",
        max_length=20,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            "type": "tel",
            "inputmode": "numeric",
            "placeholder": "+3706..."
        })
    )


def clean_starts_at(self):
    starts_at = self.cleaned_data["starts_at"]
    if starts_at < timezone.now():
        raise forms.ValidationError("Treniruočių negalima kurti praeityje.")
    return starts_at