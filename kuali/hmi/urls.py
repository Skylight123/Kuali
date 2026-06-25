from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from . import views


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="hmi", permanent=False), name="root"),
    path("hmi/", views.hmi_dashboard, name="hmi"),
    path("login/", views.login_view, name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("signup/", views.signup_view, name="signup"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("change-password/", views.change_password_view, name="change_password"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("api/robot-queue/", views.robot_queue_api, name="robot_queue_api"),
    path("api/robot-order/", views.robot_order_api, name="robot_order_api"),
    path("api/broker-status/", views.broker_status_api, name="broker_status_api"),
    path("api/broker-reconnect/", views.broker_reconnect_api, name="broker_reconnect_api"),
    path("api/modbus-config/", views.modbus_config_api, name="modbus_config_api"),
    path("api/modbus-status/", views.modbus_status_api, name="modbus_status_api"),
    path("api/modbus-reconnect/", views.modbus_reconnect_api, name="modbus_reconnect_api"),
    path("api/modbus-read/", views.modbus_read_api, name="modbus_read_api"),
    path("api/modbus-write/", views.modbus_write_api, name="modbus_write_api"),
]
