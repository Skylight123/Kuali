from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from databases import emailotpmodels
from hmi.models import EmailOTP, UserProfile


class AuthFlowTests(TestCase):
    def test_signup_verify_otp_creates_operator_profile_and_requires_login(self):
        response = self.client.post(reverse("signup"), {
            "first_name": "Line Operator",
            "username": "line_operator",
            "email": "operator@example.local",
            "password": "TemporaryPass123",
            "confirm_password": "TemporaryPass123",
        })

        self.assertRedirects(response, reverse("verify_otp"))
        self.assertEqual(self.client.session.get("otp_purpose"), "signup")
        otp = emailotpmodels.get_latest_otp("operator@example.local")
        self.assertIsNotNone(otp)

        response = self.client.post(reverse("verify_otp"), {"otp": otp.otp})

        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="line_operator")
        self.assertTrue(UserProfile.objects.filter(user=user, app_role="operator").exists())
        self.assertFalse("_auth_user_id" in self.client.session)
        self.assertFalse(EmailOTP.objects.filter(email__iexact="operator@example.local").exists())

    def test_login_with_remember_sets_long_session(self):
        User.objects.create_user(
            username="operator_login",
            email="operator-login@example.local",
            password="TemporaryPass123",
        )

        response = self.client.post(reverse("login"), {
            "username": "operator-login@example.local",
            "password": "TemporaryPass123",
            "remember": "on",
        })

        self.assertRedirects(response, reverse("hmi"))
        self.assertGreater(self.client.session.get_expiry_age(), 30000000)

    def test_forgot_password_verify_otp_enables_change_password(self):
        user = User.objects.create_user(
            username="reset_operator",
            email="reset@example.local",
            password="TemporaryPass123",
        )

        response = self.client.post(reverse("forgot_password"), {"email": "reset@example.local"})

        self.assertRedirects(response, reverse("verify_otp"))
        self.assertEqual(self.client.session.get("otp_purpose"), "reset_password")
        self.assertEqual(self.client.session.get("otp_user_id"), user.id)
        otp = emailotpmodels.get_latest_otp("reset@example.local")

        response = self.client.post(reverse("verify_otp"), {"otp": otp.otp})

        self.assertRedirects(response, reverse("change_password"))
        self.assertEqual(self.client.session.get("password_reset_user_id"), user.id)

        response = self.client.post(reverse("change_password"), {
            "password": "TemporaryPass124",
            "confirm_password": "TemporaryPass124",
        })

        self.assertRedirects(response, reverse("login"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("TemporaryPass124"))
