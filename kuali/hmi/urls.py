from django.urls import path

from . import views


urlpatterns = [
    path("", views.hmi_dashboard, name="hmi"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("change-password/", views.change_password_view, name="change_password"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
]
