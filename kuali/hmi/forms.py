from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from databases import usermodels


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Email atau username",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "auth-input",
                "placeholder": "nama@dapurmu.id",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Kata sandi",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "••••••••",
                "autocomplete": "current-password",
            }
        ),
    )


class SignUpForm(forms.ModelForm):
    email = forms.EmailField(
        label="Email kerja",
        widget=forms.EmailInput(
            attrs={
                "class": "auth-input",
                "placeholder": "nama@perusahaan.com",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Minimal 8 karakter",
                "autocomplete": "new-password",
            }
        ),
    )
    confirm_password = forms.CharField(
        label="Konfirmasi password",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Ulangi password",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["first_name", "username", "email"]
        labels = {
            "first_name": "Nama operator",
            "username": "Username",
            "email": "Email kerja",
        }
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "auth-input",
                    "placeholder": "Nama lengkap",
                    "autocomplete": "name",
                }
            ),
            "username": forms.TextInput(
                attrs={
                    "class": "auth-input",
                    "placeholder": "operator01",
                    "autocomplete": "username",
                }
            ),
        }

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if usermodels.username_exists(username):
            raise forms.ValidationError("Username ini sudah terdaftar.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if usermodels.email_exists(email):
            raise forms.ValidationError("Email ini sudah terdaftar.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Password tidak sama.")

        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)

        return cleaned_data


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label="Email akun",
        widget=forms.EmailInput(
            attrs={
                "class": "auth-input",
                "placeholder": "nama@perusahaan.com",
                "autocomplete": "email",
            }
        ),
    )


class ChangePasswordForm(forms.Form):
    password = forms.CharField(
        label="Password baru",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Minimal 8 karakter",
                "autocomplete": "new-password",
            }
        ),
    )
    confirm_password = forms.CharField(
        label="Konfirmasi password",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Ulangi password baru",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Password tidak sama.")

        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)

        return cleaned_data


class OTPForm(forms.Form):
    otp = forms.CharField(
        label="Kode OTP",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "auth-input otp-input",
                "placeholder": "000000",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
            }
        ),
    )
