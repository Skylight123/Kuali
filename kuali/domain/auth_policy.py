def dashboard_allowed(user):
    return bool(user and user.is_authenticated)
