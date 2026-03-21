"""
monitoring/forms.py
Forms used in the monitoring application.
"""

from django import forms
from .models import Profile, Pond, Farm

class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ['name', 'location', 'status']




class PondForm(forms.ModelForm):
    """Form to create or edit a Pond. The farm is set automatically in the view."""
    class Meta:
        model = Pond
        fields = ['name', 'fish_species', 'fish_count', 'status']


class ProfileForm(forms.ModelForm):
    """
    Form that combines User fields (first_name, last_name, email)
    with Profile fields (phone, role) into a single form.
    The view saves User and Profile separately.
    """

    # Extra fields from the User model
    first_name = forms.CharField(max_length=150, required=False, label='First Name')
    last_name  = forms.CharField(max_length=150, required=False, label='Last Name')
    email      = forms.EmailField(required=False, label='Email')

    class Meta:
        model  = Profile
        fields = ['phone', 'role']  # Profile-only fields

    def __init__(self, *args, **kwargs):
        # Accept the user object so we can pre-fill User fields
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial  = self.user.last_name
            self.fields['email'].initial      = self.user.email
