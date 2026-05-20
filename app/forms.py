from django import forms
from django.contrib.auth.models import User
from .models import VILOYATLAR


class RegisterForm(forms.Form):
    nickname = forms.CharField(max_length=50, label="Nik-name")
    email = forms.EmailField(label="Gmail")
    password = forms.CharField(widget=forms.PasswordInput, label="Parol")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Parolni takrorlang")
    phone = forms.CharField(max_length=20, label="Telefon")
    avatar = forms.ImageField(required=False, label="Rasm")
    region = forms.ChoiceField(choices=[('', 'Viloyatni tanlang')] + list(VILOYATLAR), required=False, label="Viloyat")

    def clean_nickname(self):
        nickname = self.cleaned_data['nickname']
        if User.objects.filter(username=nickname).exists():
            raise forms.ValidationError("Bu nik-name allaqachon band!")
        return nickname

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        if pwd and confirm and pwd != confirm:
            raise forms.ValidationError("Parollar mos kelmadi!")
        return cleaned_data


class VerifyForm(forms.Form):
    code = forms.CharField(max_length=6, label="SMS kod", widget=forms.TextInput(attrs={
        'placeholder': '000000', 'maxlength': '6', 'class': 'text-center text-2xl tracking-widest'
    }))


class LoginForm(forms.Form):
    nickname = forms.CharField(max_length=50, label="Nik-name")
    password = forms.CharField(widget=forms.PasswordInput, label="Parol")
