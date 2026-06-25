from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse, set_script_prefix

from databases import emailotpmodels
from devices.plc import registers as R
from hmi.models import EmailOTP, RobotOrder, RobotOrderTask, UserProfile
from services import robot_queue_service


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

class FakeGateway:
    def __init__(self, registers):
        self.registers = registers
        self.command_writes = []

    def read_all(self):
        return {"registers": self.registers}

    def write_command(self, address, value):
        self.command_writes.append((address, value))

    def close(self):
        pass


class FakePublisher:
    def __init__(self):
        self.events = []

    def publish_status(self, order_id, status, message=""):
        self.events.append({"order_id": order_id, "status": status, "message": message})


@override_settings(MQTT_ENABLED=False)
class RobotQueueServiceTests(TestCase):
    def ready_gateway(self):
        return FakeGateway({R.CMD_11: 1, R.STIRRER_1: 0, R.STIRRER_2: 0})

    def test_order_qty_expands_to_stirrer_tasks_and_second_order_queues(self):
        publisher = FakePublisher()
        gateway = self.ready_gateway()
        robot_queue_service.receive_order({
            "order_id": "ORD-0007",
            "items": [
                {"menu": "mie_goreng", "option": 0, "qty": 2},
                {"menu": "es_teh", "option": 0, "qty": 1},
            ],
        }, plc_gateway=gateway, publisher=publisher)

        self.assertEqual(gateway.command_writes, [(R.CMD_9, 1), (R.CMD_10, 1)])
        first_rows = list(RobotOrderTask.objects.order_by("id"))
        self.assertEqual(len(first_rows), 2)
        self.assertEqual([row.assigned_stirrer for row in first_rows], [1, 2])
        self.assertEqual([row.status for row in first_rows], [RobotOrderTask.STATUS_PROCESSING, RobotOrderTask.STATUS_PROCESSING])
        self.assertIn({"order_id": "ORD-0007", "status": RobotOrder.STATUS_PROCESSING, "message": ""}, publisher.events)

        robot_queue_service.receive_order({
            "order_id": "ORD-0008",
            "items": [
                {"menu": "mie_goreng", "option": 1, "qty": 1},
                {"menu": "mie_goreng", "option": 2, "qty": 1},
                {"menu": "es_teh", "option": 0, "qty": 1},
            ],
        }, plc_gateway=gateway, publisher=publisher)

        self.assertEqual(gateway.command_writes, [(R.CMD_9, 1), (R.CMD_10, 1)])
        rows = list(RobotOrderTask.objects.order_by("id"))
        self.assertEqual([(r.order.order_id, r.option, r.display_status) for r in rows], [
            ("ORD-0007", 0, "process stirrer 1"),
            ("ORD-0007", 0, "process stirrer 2"),
            ("ORD-0008", 1, "antri"),
            ("ORD-0008", 2, "antri"),
        ])
        self.assertIn({"order_id": "ORD-0008", "status": RobotOrder.STATUS_RECEIVED, "message": ""}, publisher.events)

    def test_plc_not_on_publishes_error_feedback(self):
        publisher = FakePublisher()
        order = robot_queue_service.receive_order({
            "order_id": "ORD-0009",
            "items": [{"menu": "mie_goreng", "option": 0, "qty": 1}],
        }, plc_gateway=FakeGateway({R.CMD_11: 0, R.STIRRER_1: 0, R.STIRRER_2: 0}), publisher=publisher)

        order.refresh_from_db()
        self.assertEqual(order.aggregate_status, RobotOrder.STATUS_ERROR)
        self.assertEqual(order.tasks.first().status, RobotOrderTask.STATUS_ERROR)
        self.assertEqual(publisher.events[-1]["status"], RobotOrder.STATUS_ERROR)
        self.assertIn("cmd_11", publisher.events[-1]["message"])

    def test_plc_on_but_stirrers_busy_keeps_order_queued(self):
        publisher = FakePublisher()
        order = robot_queue_service.receive_order({
            "order_id": "ORD-0011",
            "items": [{"menu": "mie_goreng", "option": 2, "qty": 1}],
        }, plc_gateway=FakeGateway({R.CMD_11: 1, R.STIRRER_1: 1, R.STIRRER_2: 1}), publisher=publisher)

        order.refresh_from_db()
        task = order.tasks.get()
        self.assertEqual(order.aggregate_status, RobotOrder.STATUS_RECEIVED)
        self.assertEqual(task.status, RobotOrderTask.STATUS_RECEIVED)
        self.assertEqual(task.display_status, "antri")
        self.assertEqual(publisher.events[-1]["status"], RobotOrder.STATUS_RECEIVED)

    def test_processing_task_done_when_plc_seen_on_then_off(self):
        publisher = FakePublisher()
        robot_queue_service.receive_order({
            "order_id": "ORD-0010",
            "items": [{"menu": "mie_goreng", "option": 0, "qty": 1}],
        }, plc_gateway=FakeGateway({R.CMD_11: 1, R.STIRRER_1: 0}), publisher=publisher)

        task = RobotOrderTask.objects.get()
        self.assertEqual(task.status, RobotOrderTask.STATUS_PROCESSING)

        robot_queue_service.reconcile_plc_state({"registers": {R.CMD_11: 1, R.STIRRER_1: 1}}, publisher=publisher)
        task.refresh_from_db()
        self.assertTrue(task.plc_seen_on)

        robot_queue_service.reconcile_plc_state({"registers": {R.CMD_11: 1, R.STIRRER_1: 0}}, publisher=publisher)
        task.refresh_from_db()
        task.order.refresh_from_db()
        self.assertEqual(task.status, RobotOrderTask.STATUS_DONE)
        self.assertEqual(task.order.aggregate_status, RobotOrder.STATUS_DONE)
        self.assertEqual(publisher.events[-1]["status"], RobotOrder.STATUS_DONE)



@override_settings(PLC_ENABLED=False, MODBUS_MODE="simulator", ALLOWED_HOSTS=["testserver"])
class ModbusApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="modbus_operator", password="TemporaryPass123")
        self.client.login(username="modbus_operator", password="TemporaryPass123")

    def test_modbus_config_read_and_write_use_registered_addresses(self):
        response = self.client.get("/api/modbus-config/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("functions", response.json())

        response = self.client.post(
            "/api/modbus-read/",
            data={"function_code": R.READ_HOLDING, "address": R.STIRRER_1, "quantity": 2},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["values"]), 2)

        response = self.client.post(
            "/api/modbus-read/",
            data={"function_code": R.READ_COIL, "address": R.CMD_9, "quantity": 1},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/modbus-read/",
            data={"function_code": R.READ_COIL, "address": R.SCANNER_COIL_START, "quantity": R.SCANNER_COIL_QUANTITY},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["values"]), R.SCANNER_COIL_QUANTITY)

        response = self.client.post(
            "/api/modbus-reconnect/",
            data={},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

        response = self.client.post(
            "/api/modbus-write/",
            data={"function_code": R.WRITE_SINGLE_COIL, "address": R.CMD_9, "values": [1]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["values"], [1])

        response = self.client.post(
            "/api/modbus-write/",
            data={"function_code": R.WRITE_SINGLE_COIL, "address": R.STIRRER_1, "values": [1]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
