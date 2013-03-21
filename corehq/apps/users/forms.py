from django import forms
from django.contrib import messages
from django.core.validators import EmailValidator, email_re
from django.forms.widgets import PasswordInput, HiddenInput
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _, ugettext_noop
from dimagi.utils.decorators.memoized import memoized
from hqstyle.forms.widgets import BootstrapCheckboxInput, BootstrapDisabledInput
from dimagi.utils.timezones.fields import TimeZoneField
from dimagi.utils.timezones.forms import TimeZoneChoiceField
from corehq.apps.users.models import CouchUser, WebUser, OldRoles, DomainMembership
from corehq.apps.users.util import format_username
from corehq.apps.app_manager.models import validate_lang
import re

def wrapped_language_validation(value):
    try:
        validate_lang(value)
    except ValueError:
        raise forms.ValidationError("%s is not a valid language code! Please "
                                    "enter a valid two or three digit code." % value)

class LanguageField(forms.CharField):
    """
    Adds language code validation to a field
    """
    def __init__(self, *args, **kwargs):
        super(LanguageField, self).__init__(*args, **kwargs)
        self.min_length = 2
        self.max_length = 3
    
    default_error_messages = {
        'invalid': _(u'Please enter a valid two or three digit language code.'),
    }
    default_validators = [wrapped_language_validation]

class ProjectSettingsForm(forms.Form):
    """
    Form for updating a user's project settings
    """
    global_timezone = forms.CharField(initial="UTC",
        label="Project Timezone",
        widget=BootstrapDisabledInput(attrs={'class': 'input-xlarge'}))
    override_global_tz = forms.BooleanField(initial=False,
        required=False,
        label="",
        widget=BootstrapCheckboxInput(attrs={'data-bind': 'checked: override_tz, event: {change: updateForm}'},
            inline_label="Override project's timezone setting"))
    user_timezone = TimeZoneChoiceField(label="My Timezone",
        initial=global_timezone.initial,
        widget=forms.Select(attrs={'class': 'input-xlarge', 'bindparent': 'visible: override_tz',
                                   'data-bind': 'event: {change: updateForm}'}))

    def clean_user_timezone(self):
        data = self.cleaned_data['user_timezone']
        timezone_field = TimeZoneField()
        timezone_field.run_validators(data)
        return smart_str(data)

    def save(self, web_user, domain):
        try:
            timezone = self.cleaned_data['global_timezone']
            override = self.cleaned_data['override_global_tz']
            if override:
                timezone = self.cleaned_data['user_timezone']
            dm = web_user.get_domain_membership(domain)
            dm.timezone = timezone
            dm.override_global_tz = override
            web_user.save()
            return True
        except Exception:
            return False


class RoleForm(forms.Form):

    def __init__(self, *args, **kwargs):
        if kwargs.has_key('role_choices'):
            role_choices = kwargs.pop('role_choices')
        else:
            role_choices = ()
        super(RoleForm, self).__init__(*args, **kwargs)
        self.fields['role'].choices = role_choices


class UserForm(RoleForm):
    """
        Form for updating Mobile Workers and Web Users and creating Web Users
    """

    #username = forms.CharField(max_length=15)
    first_name = forms.CharField(max_length=50, required=False, label=ugettext_noop("First Name"))
    last_name = forms.CharField(max_length=50, required=False, label=ugettext_noop("Last Name"))
    email = forms.EmailField(label=ugettext_noop("Email"), max_length=75, required=False)
    language = LanguageField(required=False,
                             label=ugettext_noop("Language"),
                             help_text=ugettext_noop("CloudCare only: write in the language code to set the "
                                                     "language this user sees in CloudCare applications. This does "
                                                     "not affect the default language of mobile applications."))
    role = forms.ChoiceField(choices=(), required=False, label=ugettext_noop("Role"))

    def __init__(self, request=None, domain=None, *args, **kwargs):
        self.request = request
        self.domain = domain
        super(UserForm, self).__init__(*args, **kwargs)
        if not self.can_change_roles:
            del self.fields['role']

    @property
    @memoized
    def can_change_roles(self):
        return self.request.user.is_superuser or self.request.couch_user.can_edit_web_users(domain=self.domain)

    @property
    def direct_props(self):
        return ['first_name', 'last_name', 'email', 'language']

    def update_user(self, existing_user=None):
        if not existing_user:
            from django.contrib.auth.models import User
            django_user = User()
            django_user.username = self.cleaned_data['email']
            django_user.save()
            existing_user = CouchUser.from_django_user(django_user)
            existing_user.save()
        for prop in self.direct_props:
            setattr(existing_user, prop, self.cleaned_data[prop])

        if self.can_change_roles and self.request.couch_user.user_id != existing_user.user_id:
            role = self.cleaned_data['role']
            if role:
                existing_user.set_role(self.domain, role)
        messages.success(self.request, _('Changes saved for user "%s"') % existing_user.username)
        existing_user.save()

    def initialize_form(self, existing_user=None):
        if not existing_user:
            return
        for prop in self.direct_props:
            self.initial[prop] = getattr(existing_user, prop, "")
        if self.can_change_roles:
            if existing_user.is_commcare_user():
                role = existing_user.get_role(self.domain)
                if role is None:
                    initial = "none"
                else:
                    initial = role.get_qualified_id()
                self.initial['role'] = initial
            else:
                self.initial['role'] = existing_user.get_role(self.domain, include_teams=False).get_qualified_id() or ''


    
    
class Meta:
        app_label = 'users'


class CommCareAccountForm(forms.Form):
    """
    Form for CommCareAccounts
    """
    username = forms.CharField(max_length=15, required=True, label=ugettext_noop("Username"))
    password = forms.CharField(widget=PasswordInput(), required=True, min_length=1,
                               label=ugettext_noop("Password"),
                               help_text=ugettext_noop("Only numbers are allowed in passwords"))
    password_2 = forms.CharField(label=ugettext_noop('Confirm Password'), widget=PasswordInput(),
                                 required=True, min_length=1)
    domain = forms.CharField(widget=HiddenInput())
    
    class Meta:
        app_label = 'users'

    def clean_username(self):
        username = self.cleaned_data['username']
        if username == 'admin' or username == 'demo_user':
            raise forms.ValidationError(_("The username %s is reserved for CommCare.") % username)
        return username
    
    def clean(self):
        try:
            password = self.cleaned_data['password']
            password_2 = self.cleaned_data['password_2']
        except KeyError:
            pass
        else:
            if password != password_2:
                raise forms.ValidationError(_("Passwords do not match"))
            if self.password_format == 'n' and not password.isnumeric():
                raise forms.ValidationError(_("Password is not numeric"))

        try:
            username = self.cleaned_data['username']
        except KeyError:
            pass
        else:
            validate_username('%s@commcarehq.org' % username)
            domain = self.cleaned_data['domain']
            username = format_username(username, domain)
            num_couch_users = len(CouchUser.view("users/by_username",
                                                 key=username))
            if num_couch_users > 0:
                raise forms.ValidationError(_("CommCare user already exists"))

            # set the cleaned username to user@domain.commcarehq.org
            self.cleaned_data['username'] = username
        return self.cleaned_data

validate_username = EmailValidator(email_re, _(u'Username contains invalid characters.'), 'invalid')


