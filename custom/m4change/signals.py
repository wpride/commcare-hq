from casexml.apps.case.signals import cases_received
from django.core.exceptions import ObjectDoesNotExist
from custom.m4change.constants import M4CHANGE_DOMAINS, ALL_M4CHANGE_FORMS, TEST_DOMAIN, IMMUNIZATION_FORMS, \
    BOOKED_DELIVERY_FORMS, UNBOOKED_DELIVERY_FORMS, BOOKING_FORMS, FOLLOW_UP_FORMS
from custom.m4change.fixtures.report_fixtures import get_last_month
from custom.m4change.models import FixtureReportResult, McctStatus
from custom.m4change.reports.reports import M4ChangeReportDataSource
from custom.m4change.utils import get_user_by_id


def _create_mcct_status_row(form_id, status, domain, received_on, registration_date, immunized, is_booking):
    try:
        mcct_status = McctStatus.objects.get(form_id__exact=form_id)
        mcct_status.status = status
        mcct_status.domain = domain
        mcct_status.received_on = received_on
        mcct_status.registration_date = registration_date
        mcct_status.immunized = immunized
        mcct_status.is_booking = is_booking
        mcct_status.save()
    except ObjectDoesNotExist:
        mcct_status = McctStatus(form_id=form_id, status=status, domain=domain,
                                 received_on=received_on, registration_date=registration_date,
                                 immunized=immunized, is_booking=is_booking)
        mcct_status.save()


def _get_registration_date(form, case):
    if form.xmlns in BOOKING_FORMS + UNBOOKED_DELIVERY_FORMS:
        return form.received_on.date()
    parent = case.parent
    mother_case = case if parent is None else parent
    return mother_case.booking if hasattr(mother_case, "booking") else case.opened_on.date()


def _handle_duplicate_form(xform, cases):
    for case in cases:
        forms = case.get_forms()
        for form in forms:
            if xform.xmlns == form.xmlns and xform._id != form._id and \
                            xform.received_on.date() == form.received_on.date():
                form.archive()
                return


def _filter_forms(xform, cases):
    """
        Every time a form is submitted go through the related cases' histories
        and update the statuses for all relevant records.
        Booking forms are always set to 'eligible', whereas immunization, booked-and unbooked delivery
        forms are 'eligible' only in case the 'immunization_given' field is present and not empty.
        In all other cases the last form's status is set to 'eligible', while the others are 'hidden'.
    """
    forms = []
    save_indices = []
    immunized = False
    invalid_forms = [status.form_id for status in
                     McctStatus.objects.filter(status__in=["rejected", "reviewed", "approved", "paid"])]
    for case in cases:
        forms += [(form_object, _get_registration_date(form_object, case), form_object.received_on)
                  for form_object in case.get_forms() if form_object._id not in invalid_forms]
    forms = sorted(forms, key=lambda f:f[2])
    pnc_forms = [form for form in forms if form[0].xmlns
                 in IMMUNIZATION_FORMS + BOOKED_DELIVERY_FORMS + UNBOOKED_DELIVERY_FORMS
                 if len(form[0].form.get("immunization_given", "")) > 0]
    for index in range(0, len(forms)):
        form = forms[index][0]
        registration_date = forms[index][1]
        if form.xmlns in BOOKING_FORMS:
            _create_mcct_status_row(form._id, "eligible", form.domain, form.received_on.date(),
                                    registration_date, False, True)
            save_indices.append(index)
        elif form.xmlns in IMMUNIZATION_FORMS + BOOKED_DELIVERY_FORMS + UNBOOKED_DELIVERY_FORMS \
                and len(form.form.get("immunization_given", "")) > 0\
                and (len(pnc_forms) < 1 or (len(pnc_forms) > 0 and pnc_forms[0][0]._id == form._id)):
            _create_mcct_status_row(form._id, "eligible", form.domain, form.received_on.date(),
                                    registration_date, True, False)
            immunized = True
            save_indices.insert(0, index)
    for index in save_indices:
        del forms[index]
    for index in range(0, len(forms)):
        form = forms[index][0]
        registration_date = forms[index][1]
        status = "hidden" if index < len(forms) - 1 or immunized else "eligible"
        _create_mcct_status_row(form._id, status, form.domain, form.received_on.date(),
                                registration_date, False, False)


def handle_m4change_forms(sender, xform, cases, **kwargs):
     if hasattr(xform, "domain") and xform.domain in M4CHANGE_DOMAINS and hasattr(xform, "xmlns"):
         if xform.xmlns in ALL_M4CHANGE_FORMS:
            _handle_duplicate_form(xform, cases)
         if xform.xmlns in BOOKING_FORMS + BOOKED_DELIVERY_FORMS + UNBOOKED_DELIVERY_FORMS +\
                 IMMUNIZATION_FORMS + FOLLOW_UP_FORMS:
            _filter_forms(xform, cases)


cases_received.connect(handle_m4change_forms)


def handle_fixture_update(sender, xform, cases, **kwargs):
    if hasattr(xform, "domain") and xform.domain == TEST_DOMAIN\
            and hasattr(xform, "xmlns") and xform.xmlns in ALL_M4CHANGE_FORMS:
        db = FixtureReportResult.get_db()
        data_source = M4ChangeReportDataSource()
        date_range = get_last_month()
        location_id = get_user_by_id(xform.form['meta']['userID']).get_domain_membership(xform.domain).location_id

        results_for_last_month = FixtureReportResult.get_report_results_by_key(domain=xform.domain,
                                                                               location_id=location_id,
                                                                               start_date=date_range[0].strftime("%Y-%m-%d"),
                                                                               end_date=date_range[1].strftime("%Y-%m-%d"))
        db.delete_docs(results_for_last_month)

        data_source.configure(config={
            "startdate": date_range[0],
            "enddate": date_range[1],
            "location_id": location_id,
            "domain": xform.domain
        })
        report_data = data_source.get_data()

        for report_slug in report_data:
            rows = dict(report_data[report_slug].get("data", []))
            name = report_data[report_slug].get("name")
            FixtureReportResult.save_result(xform.domain, location_id, date_range[0].date(), date_range[1].date(), report_slug, rows, name)

cases_received.connect(handle_fixture_update)
