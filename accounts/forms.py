from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Agreement, Message, Publication, Report, Review


User = get_user_model()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=20, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone_number", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ese correo ya está registrado.")
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name", "email", "phone_number")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError("Ese correo ya está registrado.")
        return email


class PublicationForm(forms.ModelForm):

    class Meta:
        model = Publication

        fields = [
            "title",
            "description",
            "image",
            "category",
            "price",
            "currency",
            "location",
            "availability",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "¿Qué quieres publicar?"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "placeholder": "Describe tu producto, servicio u oportunidad...",
                    "rows": 6
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "accept": "image/jpeg,image/png,image/webp",
                    "class": "image-input",
                }
            ),

            "category": forms.Select(),

            "price": forms.NumberInput(
                attrs={
                    "placeholder": "Precio",
                    "step": "0.01"
                }
            ),
            "currency": forms.Select(choices=(("mxn", "MXN"), ("usd", "USD"))),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("content",)
        widgets = {
            "content": forms.Textarea(
                attrs={"rows": 2, "placeholder": "Escribe un mensaje...", "maxlength": 2000}
            )
        }

    def clean_content(self):
        content = self.cleaned_data["content"].strip()
        if not content:
            raise forms.ValidationError("Escribe un mensaje antes de enviarlo.")
        return content


class AgreementForm(forms.ModelForm):
    class Meta:
        model = Agreement
        fields = ("price", "currency")

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price <= 0:
            raise forms.ValidationError("El precio debe ser mayor que cero.")
        return price


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "content")
        widgets = {"rating": forms.NumberInput(attrs={"min": 1, "max": 5})}

    def clean_rating(self):
        rating = self.cleaned_data["rating"]
        if not 1 <= rating <= 5:
            raise forms.ValidationError("La evaluación debe estar entre 1 y 5.")
        return rating


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ("reason", "description")
