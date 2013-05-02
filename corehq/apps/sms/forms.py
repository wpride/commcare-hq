from django.forms import *

class SMSForm(Form):
    country_code = CharField(help_text="Leave blank to make this the default gateway", required=False)

    def clean(self):
        if self.cleaned_data['country_code'] == '' and (not self.domain or self.domain.default_gateway() is not None):
            raise ValidationError('Cannot have multiple default gateways')
        if self.cleaned_data['country_code'].startswith('+'):
            self.cleaned_data['country_code'] = self.cleaned_data['country_code'][1:]
        if self.cleaned_data['country_code'] == '':
            self.cleaned_data['country_code'] = None
        if self.cleaned_data['country_code'] is not None and not self.cleaned_data['country_code'].isnumeric():
            raise ValidationError("The country code must be numeric")
        return super(SMSForm, self).clean()
