from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme
from decimal import Decimal

from apps.accounts.forms import CustomerRegistrationForm, CustomerLoginForm, CustomerProfileForm, AddressForm
from apps.accounts.models import CustomerProfile, Address
from apps.cart.utils import get_or_create_cart


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Profile creation or update
            budget = form.cleaned_data.get('monthly_budget') or Decimal('5000.00')
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
            profile.phone = form.cleaned_data['phone']
            profile.monthly_budget = budget
            profile.save()

            # Automatic login
            login(request, user)
            get_or_create_cart(request) # merge cart

            from apps.core.notifications import notify
            notify(user, "Welcome to SmartKart AI 🎉",
                   f"Your monthly grocery budget is set to ₹{budget}. Try the AI List Scanner to fill your cart in seconds!",
                   'SYSTEM', '/smart/scanner/')

            messages.success(request, f"Welcome to SmartKart AI, {user.first_name or user.username}! Your account has been created.")
            return redirect('core:home')
        else:
            messages.error(request, "Please correct the errors in the registration form.")
    else:
        form = CustomerRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    next_url = request.POST.get('next') or request.GET.get('next') or 'core:home'
    # Security: only follow ?next= links that point to THIS site (prevents open-redirect attacks)
    if next_url != 'core:home' and not url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = 'core:home'

    if request.method == 'POST':
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data['username_or_email'].strip()
            password = form.cleaned_data['password']

            # Check if user entered email or username
            user_obj = User.objects.filter(Q(username__iexact=username_or_email) | Q(email__iexact=username_or_email)).first()
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)
            else:
                user = None

            if user is not None:
                if not user.is_active:
                    messages.error(request, "Your account has been deactivated. Please contact support.")
                    return render(request, 'accounts/login.html', {'form': form})

                login(request, user)
                get_or_create_cart(request) # merge guest session cart into user cart

                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                
                # Role based redirection
                if user.is_staff or user.is_superuser:
                    if next_url and next_url != 'core:home':
                        return redirect(next_url)
                    return redirect('dashboard:admin_dashboard')
                elif hasattr(user, 'delivery_profile'):
                    if next_url and next_url != 'core:home':
                        return redirect(next_url)
                    return redirect('delivery:dashboard')

                return redirect(next_url if next_url else 'core:home')
            else:
                messages.error(request, "Invalid username/email or password.")
    else:
        form = CustomerLoginForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been securely logged out. Come back soon!")
    return redirect('core:home')


@login_required
def profile_view(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()
            form.save()
            messages.success(request, "Your profile details have been updated successfully.")
            return redirect('accounts:profile')
    else:
        initial = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }
        form = CustomerProfileForm(instance=profile, initial=initial)

    addresses = Address.objects.filter(user=request.user)
    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': profile,
        'addresses': addresses,
    })


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please fix the password errors below.")
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def address_list_view(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'accounts/address_list.html', {'addresses': addresses})


@login_required
def address_create_view(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            # If this is the user's first address, make it default
            if not Address.objects.filter(user=request.user).exists():
                address.is_default = True
            address.save()
            messages.success(request, "Delivery address added successfully.")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('accounts:address_list')
    else:
        form = AddressForm(initial={'full_name': request.user.get_full_name() or request.user.username})

    return render(request, 'accounts/address_form.html', {'form': form, 'action': 'Add New Address'})


@login_required
def address_update_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Delivery address updated successfully.")
            return redirect('accounts:address_list')
    else:
        form = AddressForm(instance=address)

    return render(request, 'accounts/address_form.html', {'form': form, 'action': 'Edit Address', 'address': address})


@login_required
def address_delete_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, "Address removed successfully.")
        return redirect('accounts:address_list')
    return render(request, 'accounts/address_confirm_delete.html', {'address': address})


@login_required
def set_default_address_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, f"'{address.full_name}' set as your default delivery address.")
    next_url = request.GET.get('next', 'accounts:address_list')
    return redirect(next_url)
