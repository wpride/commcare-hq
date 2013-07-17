from sqlagg.columns import *
from corehq.apps.reports.sqlreport import SqlTabularReport, DatabaseColumn
from corehq.apps.reports.standard import CustomProjectReport, DatespanMixin


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

        for slug in ['home_visits_pregnant', 'home_visits_postpartem', 'home_visits_newborn',
                     'home_visits_children', 'home_visits_other', 'home_visits_total']:
            columns.append(DatabaseColumn(slug, '%s_total' % slug))

        return columns
