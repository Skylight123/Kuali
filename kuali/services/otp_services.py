import logging
import random

import requests
from decouple import config
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class OTPService:
    @staticmethod
    def generate_otp(length=6):
        return random.randint(10 ** (length - 1), (10 ** length) - 1)

    @staticmethod
    def sender_email():
        return (
            getattr(settings, "DEFAULT_FROM_EMAIL", None)
            or getattr(settings, "EMAIL_HOST_USER", None)
            or "noreply@kuali.local"
        )

    @staticmethod
    def send_via_console(email, otp):
        logger.info("OTP Kuali for %s: %s", email, otp)
        print(f"[Kuali OTP] {email}: {otp}")
        return True

    @staticmethod
    def send_via_smtp(email, otp):
        send_mail(
            "Kode OTP Kuali",
            f"Kode OTP kamu adalah: {otp} (berlaku 5 menit)",
            OTPService.sender_email(),
            [email],
            fail_silently=False,
        )
        return True

    @staticmethod
    def send_via_api(email, otp):
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json={
                "sender": {"email": OTPService.sender_email()},
                "to": [{"email": email}],
                "subject": "Kode OTP Kuali",
                "htmlContent": f"<h1>{otp}</h1><p>Berlaku 5 menit</p>",
            },
            headers={
                "accept": "application/json",
                "api-key": config("API_KEY_BREVO", default=""),
                "content-type": "application/json",
            },
            timeout=15,
        )

        if 200 <= response.status_code < 300:
            return True
        raise Exception(f"Failed send OTP: {response.text}")

    @staticmethod
    def send_otp(email, method="console", otp=None):
        if otp is None:
            otp = OTPService.generate_otp()

        if method == "console":
            OTPService.send_via_console(email, otp)
        elif method == "smtp":
            OTPService.send_via_smtp(email, otp)
        elif method == "api":
            OTPService.send_via_api(email, otp)
        else:
            raise ValueError("Invalid OTP sending method")

        return otp
