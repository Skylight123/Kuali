from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from databases import emailotpmodels
from hmi.models import UserProfile
from services.otp_services import OTPService


ONE_YEAR = 60 * 60 * 24 * 365


def user_profile(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.hmi_profile
    except (AttributeError, UserProfile.DoesNotExist):
        return None


def user_app_role(user):
    profile = user_profile(user)
    return profile.app_role if profile else "operator"


def username_for_login(identifier):
    username = (identifier or "").strip()
    if "@" in username:
        matched_user = User.objects.filter(email__iexact=username).first()
        if matched_user:
            username = matched_user.username
    return username


def get_user(user_id):
    return User.objects.filter(id=user_id).first()


def find_user_by_email(email):
    return User.objects.filter(email__iexact=email).first()


def create_signup_user(signup_data):
    username = (signup_data.get("username") or "").strip()
    email = emailotpmodels.normalize_email(signup_data.get("email"))

    if User.objects.filter(username__iexact=username).exists():
        raise ValueError("Username sudah digunakan. Silakan daftar ulang.")
    if User.objects.filter(email__iexact=email).exists():
        raise ValueError("Email sudah digunakan. Silakan daftar ulang.")

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            password=signup_data["password"],
            first_name=signup_data.get("first_name", ""),
        )
        UserProfile.objects.create(user=user, app_role="operator")
    return user


def change_password(user_id, password):
    user = get_user(user_id)
    if not user:
        raise ValueError("Akun tidak ditemukan.")
    user.set_password(password)
    user.save()
    return user


def start_otp_session(request, user, purpose):
    otp_data = emailotpmodels.create_otp(user.email)

    try:
        OTPService.send_otp(
            user.email,
            method=getattr(settings, "OTP_EMAIL_METHOD", "console"),
            otp=otp_data["otp"],
        )
    except Exception:
        emailotpmodels.delete_otp(user.email)
        raise

    request.session["otp_user_id"] = user.id
    request.session["otp_purpose"] = purpose
    request.session.modified = True


def start_signup_otp_session(request, signup_data):
    signup_data = {
        **signup_data,
        "email": emailotpmodels.normalize_email(signup_data.get("email")),
    }
    otp_data = emailotpmodels.create_otp(signup_data["email"])

    try:
        OTPService.send_otp(
            signup_data["email"],
            method=getattr(settings, "OTP_EMAIL_METHOD", "console"),
            otp=otp_data["otp"],
        )
    except Exception:
        emailotpmodels.delete_otp(signup_data["email"])
        raise

    request.session["signup_data"] = signup_data
    request.session["otp_purpose"] = "signup"
    request.session.modified = True


def clear_otp_session(request):
    request.session.pop("otp_user_id", None)
    request.session.pop("otp_purpose", None)
    request.session.pop("signup_data", None)
