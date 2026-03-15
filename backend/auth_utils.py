from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser


BACKEND_USER_SESSION_KEY = 'backend_user_id'
FRONTEND_USER_SESSION_KEY = 'frontend_user_id'
BACKEND_PATH_PREFIX = '/admin-dashboard/'


def is_backend_path(path):
    return path.startswith(BACKEND_PATH_PREFIX)


def set_backend_user(request, user):
    request.session[BACKEND_USER_SESSION_KEY] = user.pk


def set_frontend_user(request, user):
    request.session[FRONTEND_USER_SESSION_KEY] = user.pk


def clear_backend_user(request):
    request.session.pop(BACKEND_USER_SESSION_KEY, None)


def clear_frontend_user(request):
    request.session.pop(FRONTEND_USER_SESSION_KEY, None)


def _get_user_by_id(user_id):
    if not user_id:
        return AnonymousUser()

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

    if not user.is_active:
        return AnonymousUser()

    return user


def get_scoped_user(request):
    session_key = BACKEND_USER_SESSION_KEY if is_backend_path(request.path) else FRONTEND_USER_SESSION_KEY
    return _get_user_by_id(request.session.get(session_key))
