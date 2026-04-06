from django import forms
from .models import Training
from django.utils import timezone
from .models import MembershipPlan
from django.core.validators import RegexValidator

class TrainingForm(forms.ModelForm):
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
            "title": "Pavadinimas",
            "starts_at": "Pradžios data ir laikas",
            "duration_minutes": "Trukmė (minutėmis)",
            "capacity": "Maksimalus dalyvių skaičius",
            "description": "Aprašymas",
            "image_url": "Paveikslėlio nuoroda",
        }

        help_texts = {
            "image_url": "Įklijuokite treniruotės paveikslėlio URL",
        }

        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "duration_minutes": forms.NumberInput(attrs={"class": "form-control"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "image_url": forms.URLInput(attrs={"class": "form-control"}),
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
