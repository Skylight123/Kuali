import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "-created_at"], name="hmi_emailot_email_idx"),
            models.Index(fields=["created_at"], name="hmi_emailot_created_idx"),
        ]
        ordering = ["-created_at", "-id"]

    def generate_otp(self):
        return str(random.randint(100000, 999999))

    def is_expired(self):
        return self.created_at < timezone.now() - timedelta(minutes=5)

    def __str__(self):
        return f"{self.email} OTP"


class UserProfile(models.Model):
    APP_ROLE_CHOICES = (
        ("operator", "Operator"),
        ("engineer", "Engineer"),
        ("supervisor", "Supervisor"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="hmi_profile")
    app_role = models.CharField(max_length=20, choices=APP_ROLE_CHOICES, default="operator")
    is_test_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    @property
    def full_name(self):
        name = self.user.get_full_name().strip()
        return name or self.user.username

    def __str__(self):
        return f"{self.user.username} - {self.get_app_role_display()}"

class RobotOrder(models.Model):
    STATUS_RECEIVED = "received"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"
    STATUS_CHOICES = (
        (STATUS_RECEIVED, "Received"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_DONE, "Done"),
        (STATUS_ERROR, "Error"),
    )

    order_id = models.CharField(max_length=64, unique=True)
    aggregate_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RECEIVED)
    raw_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["aggregate_status", "created_at"], name="hmi_robot_order_status_idx"),
        ]

    def __str__(self):
        return f"{self.order_id} - {self.aggregate_status}"


class RobotOrderTask(models.Model):
    STATUS_RECEIVED = "received"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"
    STATUS_CHOICES = (
        (STATUS_RECEIVED, "Antri"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_DONE, "Done"),
        (STATUS_ERROR, "Error"),
    )

    order = models.ForeignKey(RobotOrder, on_delete=models.CASCADE, related_name="tasks")
    menu = models.CharField(max_length=120)
    option = models.IntegerField(default=0)
    qty_index = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RECEIVED)
    assigned_stirrer = models.PositiveSmallIntegerField(blank=True, null=True)
    plc_seen_on = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["status", "assigned_stirrer"], name="hmi_robot_task_state_idx"),
            models.Index(fields=["created_at", "id"], name="hmi_robot_task_queue_idx"),
        ]

    @property
    def display_status(self):
        if self.status == self.STATUS_RECEIVED:
            return "antri"
        if self.status == self.STATUS_PROCESSING and self.assigned_stirrer:
            return f"process stirrer {self.assigned_stirrer}"
        if self.status == self.STATUS_ERROR:
            return "error"
        return self.status

    def __str__(self):
        return f"{self.order.order_id} option {self.option} - {self.display_status}"

