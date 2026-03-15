from .models import AdminNotification, SiteBranding


def admin_panel_context(request):
    try:
        site_branding = SiteBranding.get_solo()
    except Exception:
        site_branding = SiteBranding()

    notifications = AdminNotification.objects.none()
    order_notifications = AdminNotification.objects.none()
    user_notifications = AdminNotification.objects.none()
    contact_notifications = AdminNotification.objects.none()
    unread_total = 0
    order_unread_total = 0
    user_unread_total = 0
    contact_unread_total = 0

    if request.user.is_authenticated and (request.user.is_superuser or getattr(request.user, 'user_type', None) == 0):
        notifications = AdminNotification.objects.order_by('-created_at')[:10]
        order_notifications = AdminNotification.objects.filter(
            notification_type=AdminNotification.TYPE_ORDER
        ).order_by('-created_at')[:10]
        user_notifications = AdminNotification.objects.filter(
            notification_type=AdminNotification.TYPE_USER
        ).order_by('-created_at')[:10]
        contact_notifications = AdminNotification.objects.filter(
            notification_type=AdminNotification.TYPE_CONTACT
        ).order_by('-created_at')[:10]
        unread_total = AdminNotification.objects.filter(is_read=False).count()
        order_unread_total = AdminNotification.objects.filter(
            notification_type=AdminNotification.TYPE_ORDER,
            is_read=False,
        ).count()
        user_unread_total = AdminNotification.objects.filter(
            notification_type=AdminNotification.TYPE_USER,
            is_read=False,
        ).count()
        contact_unread_total = AdminNotification.objects.filter(
            notification_type=AdminNotification.TYPE_CONTACT,
            is_read=False,
        ).count()

    return {
        'site_branding': site_branding,
        'admin_notifications': notifications,
        'admin_order_notifications': order_notifications,
        'admin_user_notifications': user_notifications,
        'admin_contact_notifications': contact_notifications,
        'admin_notification_unread_total': unread_total,
        'admin_order_unread_total': order_unread_total,
        'admin_user_unread_total': user_unread_total,
        'admin_contact_unread_total': contact_unread_total,
    }
