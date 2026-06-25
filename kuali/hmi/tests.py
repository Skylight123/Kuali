from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse, set_script_prefix

from databases import emailotpmodels
from hmi.models import EmailOTP, UserProfile


@override_settings(
    FORCE_SCRIPT_NAME=None,
    STATIC_URL='/static/',
    MEDIA_URL='/media/',
    OTP_EMAIL_METHOD='console',
)
class AuthFlowTests(TestCase):
    def setUp(self):
        set_script_prefix('/')

    def test_hmi_dashboard_uses_hmi_url_not_root(self):
        self.assertEqual(reverse("hmi"), "/hmi/")

        response = self.client.get("/")
        self.assertRedirects(response, reverse("hmi"), fetch_redirect_response=False)

        response = self.client.get(reverse("hmi"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('hmi')}",
            fetch_redirect_response=False,
        )

    def test_auth_pages_render_with_login_design(self):
        response = self.client.get(reverse("signup"))
        self.assertContains(response, "Daftar akun")
        self.assertContains(response, "Kitchen Unit - Adaptive Line Intelligence")

        response = self.client.get(reverse("forgot_password"))
        self.assertContains(response, "Reset")
        self.assertContains(response, "Kitchen Unit - Adaptive Line Intelligence")

        user = User.objects.create_user(
            username="render_operator",
            email="render@example.local",
            password="TemporaryPass123",
        )
        session = self.client.session
        session["password_reset_user_id"] = user.id
        session.save()

        response = self.client.get(reverse("change_password"))
        self.assertContains(response, "Buat sandi")
        self.assertContains(response, "Kitchen Unit - Adaptive Line Intelligence")

        session = self.client.session
        session["otp_purpose"] = "signup"
        session["signup_data"] = {"email": "render@example.local"}
        session.save()

        response = self.client.get(reverse("verify_otp"))
        self.assertContains(response, "Verifikasi")
        self.assertContains(response, "render@example.local")

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

    def test_auth_user_username_and_password_reach_dashboard(self):
        User.objects.create_user(
            username="KitchenOperator",
            email="kitchen-operator@example.local",
            password="TemporaryPass123",
        )

        response = self.client.post(reverse("login"), {
            "username": "kitchenoperator",
            "password": "TemporaryPass123",
        })

        self.assertRedirects(response, reverse("hmi"))
        response = self.client.get(reverse("hmi"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hmi/dashboard.html")
        self.assertContains(response, "KitchenOperator")

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

@override_settings(
    FORCE_SCRIPT_NAME='/Kuali',
    STATIC_URL='/Kuali/static/',
    MEDIA_URL='/Kuali/media/',
    OTP_EMAIL_METHOD='console',
)
class PrefixedAuthFlowTests(TestCase):
    def setUp(self):
        set_script_prefix('/Kuali/')
        User.objects.create_user(
            username="prefixed_operator",
            email="prefixed@example.local",
            password="TemporaryPass123",
        )

    def test_login_next_without_prefix_redirects_to_prefixed_hmi_dashboard(self):
        response = self.client.post("/login/", {
            "username": "prefixed_operator",
            "password": "TemporaryPass123",
            "next": "/hmi/",
        }, SCRIPT_NAME="/Kuali")

        self.assertRedirects(response, reverse("hmi"), fetch_redirect_response=False)

    def test_login_next_with_prefix_redirects_to_prefixed_hmi_dashboard(self):
        response = self.client.post("/login/", {
            "username": "prefixed_operator",
            "password": "TemporaryPass123",
            "next": "/Kuali/hmi/",
        }, SCRIPT_NAME="/Kuali")

        self.assertRedirects(response, reverse("hmi"), fetch_redirect_response=False)

