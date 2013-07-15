from datetime import timedelta
import fluff

ADULT_REGISTRATION_XMLNS = 'http://openrosa.org/formdesigner/35af30a99b8343e4dc6f15fe3a7c61d3207fa8e2'
ADULT_FOLLOWUP_XMLNS = 'http://openrosa.org/formdesigner/af5f05c6c5389959335491450381219523e4eaff'
NEWBORN_REGISTRATION_XMLNS = 'http://openrosa.org/formdesigner/2E5C67B9-041A-413C-9F03-4243ED502016'
NEWBORN_FOLLOWUP_XMLNS = 'http://openrosa.org/formdesigner/A4BCDED3-5D58-4312-AF6A-76A97C9530DB'
CHILD_REGISTRATION_XMLNS = 'http://openrosa.org/formdesigner/1DB6E1EF-AEE4-47BF-A13C-1B6CD79E8199'
CHILD_FOLLOWUP_XMLNS = 'http://openrosa.org/formdesigner/d2401a55c30432c0881f8a2f7eaa179338253051'

def _default_date(form):
    return form.received_on

def _is_child_registration(form):
    return form.xmlns == CHILD_REGISTRATION_XMLNS

def is_adult_registration(form):
    return form.xmlns == ADULT_REGISTRATION_XMLNS

# operators
EQUAL = lambda expected, reference: expected == reference
NOT_EQUAL = lambda expected, reference: expected != reference
IN = lambda expected, reference_list: expected in reference_list

class BaseCalculator(fluff.Calculator):
    """
    For this report every indicator just emits a single "total" value
    and there's no additional complexity. Everything extends this model
    """
    window = timedelta(days=1)

    @fluff.date_emitter
    def total(self, form):
        yield _default_date(form)

class ANDCalculator(BaseCalculator):
    """
    Lets you construct AND operations on filters.
    """

    def __init__(self, calculators):
        self.calculators = calculators
        assert len(self.calculators) > 1

    def filter(self, item):
        return all(calc.filter(item) for calc in self.calculators)

class ORCalculator(BaseCalculator):
    """
    Lets you construct OR operations on filters.
    """

    def __init__(self, calculators):
        self.calculators = calculators
        assert len(self.calculators) > 1

    def filter(self, item):
        return any(calc.filter(item) for calc in self.calculators)

class FilteredFormPropertyCalculator(BaseCalculator):
    """
    Enables filtering forms by xmlns and (optionally) property == value.
    Let's you easily define indicators such as:
     - all adult registration forms
     - all child registration forms with foo.bar == baz
     - all newborn followups with bippity != bop

    These can also be chained for fun and profit.
    """
    xmlns = None
    property_path = None
    property_value = None

    def __init__(self, xmlns=None, property_path=None, property_value=None,
                 operator=EQUAL, window=None):
        def _conditional_setattr(key, value):
            if value:
                setattr(self, key, value)

        _conditional_setattr('xmlns', xmlns)
        assert self.xmlns is not None

        _conditional_setattr('property_path', property_path)
        _conditional_setattr('property_value', property_value)
        self.operator = operator
        if self.property_path is not None:
            assert self.property_value is not None

        super(FilteredFormPropertyCalculator, self).__init__(window)

    def filter(self, form):
        # filter
        return (
            form.xmlns == self.xmlns and (
                self.property_path is None or
                self.operator(form.xpath(self.property_path), self.property_value)
            )
        )
