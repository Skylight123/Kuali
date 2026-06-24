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
