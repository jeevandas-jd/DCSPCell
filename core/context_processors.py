from .permissions import can_author_content, is_admin


def role_flags(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'nav_can_author_content': False, 'nav_is_admin': False}
    return {
        'nav_can_author_content': can_author_content(user),
        'nav_is_admin': is_admin(user),
    }
