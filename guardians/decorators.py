from functools import wraps

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def has_verified_google_identity(user):
    """Require a linked Google social account and a verified matching email."""
    if not user.is_authenticated or not user.email:
        return False

    linked_google = SocialAccount.objects.filter(user=user, provider="google").exists()
    verified_email = EmailAddress.objects.filter(
        user=user,
        email__iexact=user.email,
        verified=True,
    ).exists()
    return linked_google and verified_email


def parent_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url="/accounts/login/")
        if not has_verified_google_identity(request.user):
            messages.error(request, "Please sign in with Google using the email address invited by the school.")
            return redirect("account_login")
        return view_func(request, *args, **kwargs)

    return wrapper
