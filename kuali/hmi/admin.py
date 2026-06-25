from django.contrib import admin

from .models import EmailOTP, RobotOrder, RobotOrderTask, UserProfile


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "otp", "created_at")
    search_fields = ("email",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "app_role", "is_test_user", "created_at")
    list_filter = ("app_role", "is_test_user")
    search_fields = ("user__username", "user__email", "user__first_name")


class RobotOrderTaskInline(admin.TabularInline):
    model = RobotOrderTask
    extra = 0
    readonly_fields = ("created_at", "updated_at", "started_at", "completed_at")


@admin.register(RobotOrder)
class RobotOrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "aggregate_status", "created_at", "completed_at")
    list_filter = ("aggregate_status",)
    search_fields = ("order_id",)
    inlines = [RobotOrderTaskInline]


@admin.register(RobotOrderTask)
class RobotOrderTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "menu", "option", "status", "assigned_stirrer", "plc_seen_on")
    list_filter = ("status", "assigned_stirrer", "menu")
    search_fields = ("order__order_id", "menu")
