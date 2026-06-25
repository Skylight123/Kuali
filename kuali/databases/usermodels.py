from __future__ import annotations

from django.contrib.auth.models import User
from django.db import transaction

from hmi.models import UserProfile


def username_for_identifier(identifier: str) -> str | None:
    identifier = (identifier or "").strip()
    if not identifier:
        return None

    matched_user = User.objects.filter(email__iexact=identifier).only("username").first()
    if matched_user:
        return matched_user.username

    matched_user = User.objects.filter(username__iexact=identifier).only("username").first()
    if matched_user:
        return matched_user.username

    return None


def get_user(user_id):
    return User.objects.filter(id=user_id).first()


def find_user_by_email(email):
    return User.objects.filter(email__iexact=email).first()


def username_exists(username: str) -> bool:
    return User.objects.filter(username__iexact=username).exists()


def email_exists(email: str) -> bool:
    return User.objects.filter(email__iexact=email).exists()


def create_operator_user(username: str, email: str, password: str, first_name: str = ""):
    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
        )
        UserProfile.objects.create(user=user, app_role="operator")
    return user


def set_user_password(user, password: str):
    user.set_password(password)
    user.save()
    return user
