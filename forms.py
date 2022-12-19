from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

PAYMENT_CHOICES = {
    ('S', 'Stripe'),
    ('P', 'PayPal')
}


class CheckoutForm(forms.Form):
    street_address = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Sector, Street etc.'}))
    apartment_address = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Apartment'}))
    country = CountryField(blank_label='(select country)').formfield(widget=CountrySelectWidget(attrs={'class': 'form-control'}))
    state = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}))
    zip = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zip code'}))
    payment_option = forms.ChoiceField(widget=forms.RadioSelect, choices=PAYMENT_CHOICES)


class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Coupon Code',
        'aria-label': 'Recipient\'s username',
        'aria-describedby': 'button-addon2'
    }))


class RefundForm(forms.Form):
    ref_code = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}))
    email = forms.EmailField()





