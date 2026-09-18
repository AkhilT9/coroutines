from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User

INPUT_CLASS = (
    "w-full rounded-md border border-line bg-base px-3 py-2 "
    "text-ink outline-none focus:border-accent"
)


def _style(form):
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", INPUT_CLASS)


class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)
        self.fields["username"].help_text = "3 to 15 letters, numbers, or underscores."
        self.fields["password1"].help_text = "At least 8 characters."
        self.fields["password2"].help_text = ""

    def clean_username(self):
        username = self.cleaned_data["username"].lower()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("That handle is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)

    def clean(self):
        self.cleaned_data["username"] = self.cleaned_data.get("username", "").lower()
        return super().clean()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name", "bio")
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)
