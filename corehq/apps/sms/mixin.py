import re
from couchdbkit.ext.django.schema import *
import importlib

phone_number_re = re.compile("^\d+$")

class PhoneNumberException(Exception):
    pass

class InvalidFormatException(PhoneNumberException):
    pass

class PhoneNumberInUseException(PhoneNumberException):
    pass

class VerifiedNumber(Document):
    """
    There should only be one VerifiedNumber entry per (owner_doc_type, owner_id), and
    each VerifiedNumber.phone_number should be unique across all entries.

    Right now, no VerifiedNumbers are actually verified in any way--they must only be unique.
    """
    domain          = StringProperty()
    owner_doc_type  = StringProperty()
    owner_id        = StringProperty()
    phone_number    = StringProperty()
    backend_id      = StringProperty() # points to a MobileBackend
    verified        = BooleanProperty()
    
    @property
    def backend(self):
        return MobileBackend.get(self.backend_id)
    
    @property
    def owner(self):
        from corehq.apps.sms.models import CommConnectCase
        from corehq.apps.users.models import CommCareUser
        owner_classes = {'CommCareCase': CommConnectCase, 'CommCareUser': CommCareUser}
        if self.owner_doc_type in owner_classes:
            return owner_classes[self.owner_doc_type].get(self.owner_id)
        else:
            return None

class MobileBackend(Document):
    """
    Defines a backend to be used for sending / receiving SMS.
    """
    domain = ListProperty(StringProperty)   # A list of domains for which this backend is applicable
    description = StringProperty()          # (optional) A description of this backend
    outbound_module = StringProperty()      # The fully-qualified name of the inbound module to be used (must implement send() method)
    outbound_params = DictProperty()        # The parameters which will be the keyword arguments sent to the outbound module's send() method
    country_code = StringProperty()              # ID of a country document

    def applies_to(self, domain):
        return len(self.domain) == 0 or domain in self.domain

    @classmethod
    def by_domain(cls, domain):
        return cls.view('sms/backend_by_domain_and_country', startkey=[domain], endkey=[domain, {}], include_docs=True).all()

    @classmethod
    def find(cls, domain=None, country=None):
        country = str(country)
        backends = cls.view('sms/backend_by_domain_and_country', key=[domain, country], include_docs=True).all()
        if len(backends) > 0:
            return backends[0]
        backends = cls.view('sms/backend_by_domain_and_country', key=[domain, None], include_docs=True).all()
        if len(backends) > 0:
            return backends[0]
        backends = cls.view('sms/backend_by_domain_and_country', key=[None, country], include_docs=True).all()
        if len(backends) > 0:
            return backends[0]
        backends = cls.view('sms/backend_by_domain_and_country', key=[None, None], include_docs=True).all()
        if len(backends) > 0:
            return backends[0]
        return None

    def module(self):
        return importlib.import_module(self.outbound_module)

    def clean_outbound_params(self):
        outbound = self.outbound_params.copy()
        for param in self.module().API_DIRTY_PARAMS:
            del outbound[param]
        return outbound

    def form(self):
        return self.module().API_FORM(initial=self.clean_outbound_params())

    def help_message(self):
        # request may not exist so it's getattr'd rather than .'d
        return self.module().API_HELP_MESSAGE(self._request, self) # getattr(self, 'request', None)

    @property
    def default(self):
        return self.country_code is None

    def id(self):
        return self._id

class CommCareMobileContactMixin(object):
    """
    Defines a mixin to manage a mobile contact's information. This mixin must be used with
    a class which is a Couch Document.
    """
    
    def get_time_zone(self):
        """
        This method should be implemented by all subclasses of CommCareMobileContactMixin,
        and must return a string representation of the time zone. For example, "America/New_York".
        """
        raise NotImplementedError("Subclasses of CommCareMobileContactMixin must implement method get_time_zone().")
    
    def get_language_code(self):
        """
        This method should be implemented by all subclasses of CommCareMobileContactMixin,
        and must return the preferred language code of the contact. For example, "en".
        """
        raise NotImplementedError("Subclasses of CommCareMobileContactMixin must implement method get_language_code().")
    
    def get_verified_number(self):
        """
        Retrieves this contact's verified number entry by (self.doc_type, self._id).
        
        return  the VerifiedNumber entry
        """
        v = VerifiedNumber.view("sms/verified_number_by_doc_type_id",
            startkey=[self.doc_type, self._id],
            endkey=[self.doc_type, self._id],
            include_docs=True
        ).one()
        return v
    
    def validate_number_format(self, phone_number):
        """
        Validates that the given phone number consists of all digits.
        
        return  void
        raises  InvalidFormatException if the phone number format is invalid
        """
        if not phone_number_re.match(phone_number):
            raise InvalidFormatException("Phone number format must consist of only digits.")
    
    def verify_unique_number(self, phone_number):
        """
        Verifies that the given phone number is not already in use by any other contacts.
        
        return  void
        raises  InvalidFormatException if the phone number format is invalid
        raises  PhoneNumberInUseException if the phone number is already in use by another contact
        """
        self.validate_number_format(phone_number)
        v = VerifiedNumber.view("sms/verified_number_by_number",
            key=phone_number,
            include_docs=True
        ).one()
        if v is not None and (v.owner_doc_type != self.doc_type or v.owner_id != self._id):
            raise PhoneNumberInUseException("Phone number is already in use.")
    
    def save_verified_number(self, domain, phone_number, verified, backend_id):
        """
        Saves the given phone number as this contact's verified phone number.
        
        return  void
        raises  InvalidFormatException if the phone number format is invalid
        raises  PhoneNumberInUseException if the phone number is already in use by another contact
        """
        self.verify_unique_number(phone_number)
        v = self.get_verified_number()
        if v is None:
            v = VerifiedNumber(
                owner_doc_type = self.doc_type,
                owner_id = self._id
            )
        v.domain = domain
        v.phone_number = phone_number
        v.verified = verified
        v.backend_id = backend_id
        v.save()

    def delete_verified_number(self):
        """
        Deletes this contact's phone number from the verified phone number list, freeing it up
        for use by other contacts.
        
        return  void
        """
        v = self.get_verified_number()
        if v is not None:
            v.doc_type += "-Deleted"
            v.save()

    @classmethod
    def get_by_verified_number(cls, phone_number):
        vn = VerifiedNumber.view('sms/verified_number_by_default_phone', key=phone_number, include_docs=True).one()
        if vn.owner_doc_type == cls.__name__:
            return cls.get(vn.owner_id)
        else:
            return None
