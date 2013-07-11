from datetime import timedelta
import fluff

ADULT_REGISTRATION_XMLNS = 'http://openrosa.org/formdesigner/35af30a99b8343e4dc6f15fe3a7c61d3207fa8e2'
NEWBORN_REGISTRATION_XMLNS = 'http://openrosa.org/formdesigner/2E5C67B9-041A-413C-9F03-4243ED502016'
NEWBORN_FOLLOWUP_XMLNS = 'http://openrosa.org/formdesigner/A4BCDED3-5D58-4312-AF6A-76A97C9530DB'
CHILD_REGISTRATION_XMLNS = 'http://openrosa.org/formdesigner/1DB6E1EF-AEE4-47BF-A13C-1B6CD79E8199'
CHILD_FOLLOWUP_XMLNS = 'http://openrosa.org/formdesigner/d2401a55c30432c0881f8a2f7eaa179338253051'

def _default_date(form):
    return form.received_on

class FormCalculator(fluff.Calculator):
    window = timedelta(days=1)
    xmlns = None

    def __init__(self, xmlns=None, window=None):
        if xmlns:
            self.xmlns = xmlns
        assert self.xmlns is not None
        super(FormCalculator, self).__init__(window)

    def filter(self, form):
        return form.xmlns == self.xmlns

class MultiFormCalculator(fluff.Calculator):
    window = timedelta(days=1)
    xmlnses = set([])

    def __init__(self, xmlnses=None, window=None):
        if xmlnses:
            self.xmlnses = xmlnses
        assert len(self.xmlnses) > 0
        self.xmlnses = set(self.xmlnses)
        super(MultiFormCalculator, self).__init__(window)

    def filter(self, form):
        return form.xmlns in self.xmlnses

class FormCounterCalculator(FormCalculator):

    @fluff.date_emitter
    def total(self, form):
        yield _default_date(form)

class AdultIndicatorCalculator(FormCalculator):
    xmlns = ADULT_REGISTRATION_XMLNS

    @fluff.date_emitter
    def pregnant_mothers(self, form):
        if str(form.form.get('pregnant')) == '1':
            yield _default_date(form)

class NewbornVisitCalculator(MultiFormCalculator):
    xmlnses = set([NEWBORN_REGISTRATION_XMLNS, NEWBORN_FOLLOWUP_XMLNS])

    @fluff.date_emitter
    def total(self, form):
        yield _default_date(form)

class ChildVisitCalculator(MultiFormCalculator):
    xmlnses = set([CHILD_REGISTRATION_XMLNS, CHILD_FOLLOWUP_XMLNS])

    @fluff.date_emitter
    def total(self, form):
        yield _default_date(form)