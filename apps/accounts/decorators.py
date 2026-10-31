from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def customer_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to continue.")
            return redirect(f"/accounts/login/?next={request.path}")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to access the administrator portal.")
            return redirect(f"/accounts/login/?next={request.path}")
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, "Access restricted. Administrator privileges required.")
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def delivery_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please log in with your Delivery Partner account.")
            return redirect(f"/accounts/login/?next={request.path}")
        is_delivery = hasattr(request.user, 'delivery_profile') or request.user.groups.filter(name='Delivery').exists()
        if not is_delivery and not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, "Access restricted to authorized Delivery Personnel.")
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
