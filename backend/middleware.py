from django.utils.functional import SimpleLazyObject

from .auth_utils import get_scoped_user


class ScopedSessionAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda: get_scoped_user(request))
        return self.get_response(request)
