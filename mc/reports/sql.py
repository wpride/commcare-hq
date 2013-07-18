from sqlagg.columns import *
from corehq.apps.reports.sqlreport import SqlTabularReport, DatabaseColumn
from corehq.apps.reports.standard import CustomProjectReport, DatespanMixin


HF_MONTHLY_SLUGS = [
    'home_visits_pregnant',
    'home_visits_postpartem',
    'home_visits_newborn',
    'home_visits_children',
    'home_visits_other',
    'home_visits_total',
    "rdt_positive_children",
    "rdt_positive_adults",
    "rdt_others",
    "rdt_total",

    # "diagnosed cases",
    "diagnosed_malaria_child",
    "diagnosed_malaria_adult",
    "diagnosed_diarrhea",
    "diagnosed_ari",
    "diagnosed_total",

    # "treated cases",
    "treated_malaria",
    "treated_diarrhea",
    "treated_ari",
    "treated_total",

    # "transfers",
    "transfer_malnutrition",
    "transfer_incomplete_vaccination",
    "transfer_danger_signs",
    "transfer_prenatal_consult",
    "transfer_missing_malaria_meds",
    "transfer_other",
    "transfer_total",

    # "deaths",
    "deaths_newborn",
    "deaths_children",
    "deaths_mothers",
    "deaths_other",
    "deaths_total",
    "heath_ed_talks",
    "heath_ed_participants",
]

class HeathFacilityMonthly(SqlTabularReport, CustomProjectReport, DatespanMixin):
    exportable = True
    emailable = True
    slug = 'hf_monthly'
    name = "Health Facility Monthly Report"
    table_name = "mc-inscale_MalariaConsortiumFluff"

    fields = ['corehq.apps.reports.fields.DatespanField']

    @property
    def filters(self):
        return ["domain = :domain", "date between :startdate and :enddate"]


    @property
    def group_by(self):
        return ['user_id']

    @property
    def filter_values(self):
        return dict(domain=self.domain,
                    startdate=self.datespan.startdate_param_utc,
                    enddate=self.datespan.enddate_param_utc)

    @property
    def columns(self):
        user = DatabaseColumn("User", "user_id", column_type=SimpleColumn)
        columns = [user]

        for slug in HF_MONTHLY_SLUGS:
            columns.append(DatabaseColumn(slug, '%s_total' % slug))

        return columns
