from couchforms.models import XFormInstance
import fluff
from . import calculators

get_user_id = lambda form: form.metadata.userID

class MalariaConsortiumFluff(fluff.IndicatorDocument):
    document_class = XFormInstance

    domains = ('mc-inscale',)
    group_by = ('domain', fluff.AttributeGetter('user_id', get_user_id))

    adult_registrations = calculators.FormCounterCalculator(xmlns=calculators.ADULT_REGISTRATION_XMLNS)
    child_registrations = calculators.FormCounterCalculator(xmlns=calculators.CHILD_REGISTRATION_XMLNS)
    adult_indicators = calculators.AdultIndicatorCalculator()
    newborn_visits = calculators.NewbornVisitCalculator()
    child_visits = calculators.ChildVisitCalculator()

    # home visit
    class Meta:
        app_label = 'mc'

MalariaConsortiumFluffPillow = MalariaConsortiumFluff.pillow()