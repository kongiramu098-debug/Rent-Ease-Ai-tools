def unread_count(request):
    u = request.user
    return {"unread": u.notifications.filter(read=False).count() if u.is_authenticated else 0}
