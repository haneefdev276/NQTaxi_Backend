from django.contrib import admin

from apps.notifications.models import FCMDeviceToken, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type', 'created_at')
    search_fields = ('title', 'body', 'user__username', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at', 'read_at')
    raw_id_fields = ('user',)


@admin.register(FCMDeviceToken)
class FCMDeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'is_active', 'created_at')
    list_filter = ('device_type', 'is_active')
    search_fields = ('token', 'user__username', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('user',)
