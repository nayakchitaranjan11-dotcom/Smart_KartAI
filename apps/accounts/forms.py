from django import forms
from django.contrib.auth.models import User
from apps.accounts.models import CustomerProfile, DeliveryProfile, Address
from decimal import Decimal


class CustomerRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))
    phone = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number (10 digits)'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create Password (min 6 characters)'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))
    monthly_budget = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=Decimal('5000.00'),
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Optional Monthly Grocery Budget (₹)'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose Username'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class CustomerLoginForm(forms.Form):
    username_or_email = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))


class CustomerProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))

    class Meta:
        model = CustomerProfile
        fields = ['phone', 'avatar', 'monthly_budget', 'budget_warning_threshold', 'budget_reset_day']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'monthly_budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '100'}),
            'budget_warning_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': '50', 'max': '100'}),
            'budget_reset_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '28'}),
        }


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['full_name', 'phone_number', 'address_type', 'street_address', 'landmark', 'city', 'state', 'postal_code', 'is_default']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Phone Number'}),
            'address_type': forms.Select(attrs={'class': 'form-select'}),
            'street_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Flat/House No., Building Name, Street, Area'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nearby Landmark (e.g. Near Metro Station)'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '6-digit Pincode'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
