from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Message, Publication


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
            "category",
            "price",
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

            "category": forms.Select(),

            "price": forms.NumberInput(
                attrs={
                    "placeholder": "Precio",
                    "step": "0.01"
                }
            ),
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
