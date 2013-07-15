from couchforms.models import XFormInstance
import fluff
from . import calculators

get_user_id = lambda form: form.metadata.userID


class MalariaConsortiumFluff(fluff.IndicatorDocument):
    document_class = XFormInstance

    domains = ('mc-inscale',)
    group_by = ('domain', fluff.AttributeGetter('user_id', get_user_id))

    # report 1a, district - monthly

    # home visits
    home_visits_pregnant = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/pregnant',
        property_value='1',
    )
    home_visits_postpartem = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/post_partum',
        property_value='1',
    )
    internal_home_visits_newborn_reg = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.NEWBORN_REGISTRATION_XMLNS,
    )
    internal_home_visits_newborn_followup = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.NEWBORN_FOLLOWUP_XMLNS,
    )
    home_visits_newborn = calculators.ORCalculator(
         [internal_home_visits_newborn_reg, internal_home_visits_newborn_followup]
    )
    internal_home_visits_child_reg = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
    )
    internal_home_visits_child_followup = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_FOLLOWUP_XMLNS,
    )
    home_visits_children = calculators.ORCalculator(
         [internal_home_visits_child_reg, internal_home_visits_child_followup]
    )
    internal_home_visits_non_pregnant = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/pregnant',
        property_value='1',
        operator=calculators.NOT_EQUAL,
    )
    internal_home_visits_adult_followup = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_FOLLOWUP_XMLNS,
    )
    home_visits_other = calculators.ORCalculator(
         [internal_home_visits_non_pregnant, internal_home_visits_adult_followup]
    )
    home_visits_total = calculators.ORCalculator(
        [home_visits_pregnant, home_visits_postpartem, home_visits_newborn, home_visits_children, home_visits_other]
    )

    # rdt
    rdt_positive_children = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/consult/results_rdt',
        property_value='1',
    )
    rdt_positive_adults = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/rdt_result',
        property_value='1',
    )
    internal_rdt_negative_children = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/consult/results_rdt',
        property_value=set(['2', '3']),
        operator=calculators.IN,
    )
    internal_rdt_negative_adults = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/rdt_result',
        property_value=set(['2', '3']),
        operator=calculators.IN,
    )
    rdt_others = calculators.ORCalculator(
         [internal_rdt_negative_adults, internal_rdt_negative_children]
    )
    rdt_total = calculators.ORCalculator(
        [rdt_positive_children, rdt_positive_adults, rdt_others]
    )

    # diagnosed cases
    diagnosed_malaria_child = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/self_report/diagnosis_given',
        property_value='1',
    )
    diagnosed_malaria_adult = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/diagnosis_given',
        property_value='1',
    )
    internal_diagnosed_diarrhea_child = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/self_report/diagnosis_given',
        property_value='2',
    )
    internal_diagnosed_diarrhea_adult = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/diagnosis_given',
        property_value='2',
    )
    diagnosed_diarrhea = calculators.ORCalculator(
         [internal_diagnosed_diarrhea_child, internal_diagnosed_diarrhea_adult]
    )
    internal_diagnosed_ari_child = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/self_report/diagnosis_given',
        property_value='3',
    )
    # ari = acute resperatory infection
    internal_diagnosed_ari_adult  = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/diagnosis_given',
        property_value='pneumonia',
    )
    diagnosed_ari = calculators.ORCalculator(
         [internal_diagnosed_ari_child, internal_diagnosed_ari_adult]
    )
    diagnosed_total = calculators.ORCalculator(
        [diagnosed_malaria_child, diagnosed_malaria_adult, diagnosed_diarrhea, diagnosed_ari]
    )

    # treated cases
    internal_treated_malaria_child = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/self_report/treatment_given',
        property_value=set(['4', '5', '7', '8', '9', '10', '11']),
        operator=calculators.IN,
    )
    internal_diagnosed_and_treated_malaria_child = calculators.ANDCalculator(
        [diagnosed_malaria_child, internal_treated_malaria_child]
    )
    internal_treated_malaria_adult = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/treatment_given',
        property_value=set(['4', '5', '7', '8', '9', '10', '11']),
        operator=calculators.IN,
    )
    internal_diagnosed_and_treated_malaria_adult = calculators.ANDCalculator(
        [diagnosed_malaria_adult, internal_treated_malaria_adult]
    )
    treated_malaria = calculators.ORCalculator(
         [internal_diagnosed_and_treated_malaria_child, internal_diagnosed_and_treated_malaria_adult]
    )
    internal_treated_diarrhea_child = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/self_report/treatment_given',
        property_value='3',
    )
    internal_diagnosed_and_treated_diarrhea_child = calculators.ANDCalculator(
         [internal_diagnosed_diarrhea_child, internal_treated_diarrhea_child]
    )
    internal_treated_diarrhea_adult = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/treatment_given',
        property_value=set(['3', '6']),
        operator=calculators.IN,
    )
    internal_diagnosed_and_treated_diarrhea_adult = calculators.ANDCalculator(
         [internal_diagnosed_diarrhea_adult, internal_treated_diarrhea_adult]
    )
    treated_diarrhea = calculators.ORCalculator(
         [internal_diagnosed_and_treated_diarrhea_child, internal_diagnosed_and_treated_diarrhea_adult]
    )
    internal_treated_ari_child= calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/self_report/treatment_given',
        property_value=set(['1', '2']),
        operator=calculators.IN,
    )
    internal_diagnosed_and_treated_ari_child = calculators.ANDCalculator(
         [internal_diagnosed_ari_child, internal_treated_ari_child]
    )
    internal_treated_ari_adult = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/treatment_given',
        property_value=set(['1', '2']),
        operator=calculators.IN,
    )
    internal_diagnosed_and_treated_ari_adult = calculators.ANDCalculator(
         [internal_diagnosed_ari_adult, internal_treated_ari_adult]
    )
    treated_ari = calculators.ORCalculator(
        [internal_diagnosed_and_treated_ari_child, internal_diagnosed_and_treated_ari_adult]
    )
    treated_total = calculators.ORCalculator(
        [treated_malaria, treated_diarrhea, treated_ari]
    )

    # transfers
    internal_transfer_malnutrition_child = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='5',
    )
    internal_transfer_malnutrition_adult = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='5',
    )
    transfer_malnutrition = calculators.ORCalculator(
        [internal_transfer_malnutrition_child, internal_transfer_malnutrition_adult]
    )
    internal_transfer_incomplete_vaccination_child = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='3',
    )
    internal_transfer_incomplete_vaccination_newborn = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.NEWBORN_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='3',
    )
    internal_transfer_incomplete_vaccination_adult = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='3',
    )
    transfer_incomplete_vaccination = calculators.ORCalculator([
        internal_transfer_incomplete_vaccination_child,
        internal_transfer_incomplete_vaccination_newborn,
        internal_transfer_incomplete_vaccination_adult,
    ])
    internal_transfer_danger_signs_child = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='1',
    )
    internal_transfer_danger_signs_newborn = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.NEWBORN_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='1',
    )
    internal_transfer_danger_signs_adult = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='1',
    )
    transfer_danger_signs = calculators.ORCalculator([
        internal_transfer_danger_signs_child,
        internal_transfer_danger_signs_newborn,
        internal_transfer_danger_signs_adult,
    ])
    transfer_prenatal_consult = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='6',
    )
    internal_transfer_missing_malaria_meds_child = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='7',
    )
    internal_transfer_missing_malaria_meds_adult = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='7',
    )
    transfer_missing_malaria_meds = calculators.ORCalculator(
        [internal_transfer_missing_malaria_meds_child, internal_transfer_missing_malaria_meds_adult]
    )
    internal_transfer_other_child = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.CHILD_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value=set(['0', '6']),
        operator=calculators.IN,
    )
    internal_transfer_other_newborn = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.NEWBORN_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value=set(['0', '2', '4']),
        operator=calculators.IN,
    )
    internal_transfer_other_adult = calculators.FilteredFormPropertyCalculator(
        xmlns=calculators.ADULT_REGISTRATION_XMLNS,
        property_path='form/self_report/referral_given_reason',
        property_value='0',
    )
    transfer_other = calculators.ORCalculator([
        internal_transfer_other_child,
        internal_transfer_other_newborn,
        internal_transfer_other_adult,
    ])
    transfer_total = calculators.ORCalculator([
        transfer_malnutrition,
        transfer_incomplete_vaccination,
        transfer_danger_signs,
        transfer_prenatal_consult,
        transfer_missing_malaria_meds,
        transfer_other,
    ])

    class Meta:
        app_label = 'mc'

MalariaConsortiumFluffPillow = MalariaConsortiumFluff.pillow()