import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from databases import emailotpmodels
from services import auth_service
from services.auth_service import ONE_YEAR

from .forms import ChangePasswordForm, ForgotPasswordForm, LoginForm, OTPForm, SignUpForm

logger = logging.getLogger(__name__)


def _default_redirect_for_user(user):
    return redirect("hmi")


def _safe_redirect_after_login(request, next_url):
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return _default_redirect_for_user(request.user)


@login_required
def hmi_dashboard(request):
    return render(request, "hmi/dashboard.html")


def login_view(request):
    if request.user.is_authenticated:
        return _default_redirect_for_user(request.user)

    next_url = request.GET.get("next") or request.POST.get("next") or reverse("hmi")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = auth_service.username_for_login(form.cleaned_data["username"])
            user = authenticate(
                request,
                username=username,
                password=form.cleaned_data["password"],
            )
            if user is not None:
                login(request, user)
                if request.POST.get("remember"):
                    request.session.set_expiry(ONE_YEAR)
                else:
                    request.session.set_expiry(0)
                request.session.modified = True
                messages.success(request, "Login berhasil. Dashboard HMI siap dipantau.")
                return _safe_redirect_after_login(request, next_url)
            messages.error(request, "Username/email atau password tidak sesuai.")
    else:
        form = LoginForm()

    return render(request, "frontpages/login.html", {"form": form, "next": next_url})


def signup_view(request):
    if request.user.is_authenticated:
        return _default_redirect_for_user(request.user)

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            signup_data = {
                "username": form.cleaned_data["username"],
                "email": form.cleaned_data["email"],
                "first_name": form.cleaned_data.get("first_name", ""),
                "password": form.cleaned_data["password"],
            }
            try:
                _start_signup_otp_session(request, signup_data)
            except Exception:
                logger.exception("Failed sending signup OTP for email=%s", signup_data.get("email"))
                form.add_error(None, "Gagal mengirim OTP. Silakan coba lagi atau periksa email tujuan.")
                return render(request, "frontpages/signup.html", {"form": form})
            messages.success(request, "Akun berhasil dibuat. Masukkan OTP yang dikirim ke email kamu.")
            return redirect("verify_otp")
    else:
        form = SignUpForm()

    return render(request, "frontpages/signup.html", {"form": form})


def verify_otp_view(request):
    otp_purpose = request.session.get("otp_purpose")
    if not otp_purpose:
        messages.error(request, "Sesi OTP tidak ditemukan. Silakan mulai ulang.")
        return redirect("login")

    signup_data = request.session.get("signup_data") or {}
    user = None
    email = emailotpmodels.normalize_email(signup_data.get("email", ""))
    if otp_purpose != "signup":
        otp_user_id = request.session.get("otp_user_id")
        user = auth_service.get_user(otp_user_id)
        if not user:
            _clear_otp_session(request)
            messages.error(request, "Akun tidak ditemukan.")
            return redirect("login")
        email = emailotpmodels.normalize_email(user.email)

    if not email:
        _clear_otp_session(request)
        messages.error(request, "Sesi OTP tidak lengkap. Silakan mulai ulang.")
        return redirect("login")

    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_result = emailotpmodels.verify_otp(email, form.cleaned_data["otp"])
            if otp_result["status"]:
                if otp_purpose == "signup":
                    try:
                        auth_service.create_signup_user(signup_data)
                    except ValueError as exc:
                        emailotpmodels.delete_otp(email)
                        _clear_otp_session(request)
                        messages.error(request, str(exc))
                        return redirect("signup")
                    emailotpmodels.delete_otp(email)
                    _clear_otp_session(request)
                    messages.success(request, "Verifikasi berhasil. Akun operator HMI sudah aktif.")
                    return redirect("login")

                request.session["password_reset_user_id"] = user.id
                emailotpmodels.delete_otp(email)
                _clear_otp_session(request)
                messages.success(request, "OTP benar. Silakan buat password baru.")
                return redirect("change_password")

            if otp_result["message"] in {"OTP expired", "OTP expired or not found"}:
                messages.error(request, "OTP sudah kadaluarsa atau tidak ditemukan. Silakan minta OTP baru.")
            else:
                messages.error(request, "Kode OTP tidak sesuai.")
    else:
        form = OTPForm()

    return render(
        request,
        "frontpages/verify_otp.html",
        {"form": form, "email": email, "purpose": otp_purpose},
    )


def forgot_password_view(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = emailotpmodels.normalize_email(form.cleaned_data["email"])
            user = auth_service.find_user_by_email(email)
            if not user:
                form.add_error("email", "Email belum terdaftar di sistem HMI.")
                return render(request, "frontpages/forgot_password.html", {"form": form})
            try:
                _start_otp_session(request, user, purpose="reset_password")
            except Exception:
                logger.exception("Failed sending password reset OTP for email=%s", email)
                form.add_error(None, "Gagal mengirim OTP. Silakan coba lagi atau periksa email tujuan.")
                return render(request, "frontpages/forgot_password.html", {"form": form})
            messages.success(request, "OTP reset password sudah dikirim ke email kamu.")
            return redirect("verify_otp")
    else:
        form = ForgotPasswordForm()

    return render(request, "frontpages/forgot_password.html", {"form": form})


def change_password_view(request):
    password_reset_user_id = request.session.get("password_reset_user_id")
    if not password_reset_user_id:
        messages.error(request, "Sesi reset password tidak ditemukan. Silakan mulai ulang.")
        return redirect("forgot_password")

    if request.method == "POST":
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            try:
                auth_service.change_password(password_reset_user_id, form.cleaned_data["password"])
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect("forgot_password")
            request.session.pop("password_reset_user_id", None)
            messages.success(request, "Password berhasil diperbarui. Silakan login kembali.")
            return redirect("login")
    else:
        form = ChangePasswordForm()

    return render(request, "frontpages/change_password.html", {"form": form})


def _start_otp_session(request, user, purpose):
    auth_service.start_otp_session(request, user, purpose)


def _start_signup_otp_session(request, signup_data):
    auth_service.start_signup_otp_session(request, signup_data)


def _clear_otp_session(request):
    auth_service.clear_otp_session(request)
