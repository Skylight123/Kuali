from django.utils import timezone

from hmi.models import EmailOTP


OTP_EXPIRY_MINUTES = 5


def normalize_email(email):
    return (email or "").strip().lower()


def _email_otp_queryset(email):
    normalized_email = normalize_email(email)
    if not normalized_email:
        return EmailOTP.objects.none()
    return EmailOTP.objects.filter(email__iexact=normalized_email)


def create_otp(email):
    email = normalize_email(email)
    delete_expired_otps()
    delete_otp(email)

    otp_instance = EmailOTP(email=email)
    otp_instance.otp = otp_instance.generate_otp()
    otp_instance.save()

    return {
        "email": otp_instance.email,
        "otp": otp_instance.otp,
        "created_at": otp_instance.created_at,
    }


def get_latest_otp(email):
    delete_expired_otps()
    return _email_otp_queryset(email).order_by("-created_at", "-id").first()


def verify_otp(email, input_otp):
    otp = get_latest_otp(email)

    if not otp:
        return {
            "status": False,
            "message": "OTP expired or not found",
        }

    if otp.is_expired():
        delete_otp(email)
        return {
            "status": False,
            "message": "OTP expired",
        }

    if otp.otp != input_otp:
        return {
            "status": False,
            "message": "Invalid OTP",
        }

    return {
        "status": True,
        "message": "OTP valid",
    }


def delete_otp(email):
    deleted_count, _ = _email_otp_queryset(email).delete()

    return {
        "status": True,
        "message": "OTP deleted",
        "deleted": deleted_count,
    }


def delete_expired_otps():
    expired_time = timezone.now() - timezone.timedelta(minutes=OTP_EXPIRY_MINUTES)
    deleted_count, _ = EmailOTP.objects.filter(created_at__lt=expired_time).delete()

    return {
        "deleted": deleted_count,
    }
