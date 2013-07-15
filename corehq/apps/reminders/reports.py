from datetime import datetime
import pytz

from corehq.apps.reports.standard import ProjectReport
from django.utils.translation import ugettext as _
from corehq.apps.reminders.forms import RemindersInErrorForm
from corehq.apps.reminders.models import CaseReminder
from dimagi.utils.timezones import utils as tz_utils
from corehq.apps.reports import util as report_utils
from dimagi.utils.couch.database import is_bigcouch, bigcouch_quorum_count
from .util import get_recipient_name


class RemindersInErrorReport(ProjectReport):
    name = _("Reminders in Error")
    slug = "reminders_in_error"
    report_template_path = 'reminders/partial/reminders_in_error.html'
    filters = []
    hide_filters = True
    ajax_pagination = True

    @property
    def report_context(self):
        request = self.request

        handler_map = {}
        if request.method == "POST":
            form = RemindersInErrorForm(request.POST)
            if form.is_valid():
                kwargs = {}
                if is_bigcouch():
                    # Force a write to all nodes before returning
                    kwargs["w"] = bigcouch_quorum_count()
                current_timestamp = datetime.utcnow()
                for reminder_id in form.cleaned_data.get("selected_reminders"):
                    reminder = CaseReminder.get(reminder_id)
                    if reminder.domain != self.domain:
                        continue
                    if reminder.handler_id in handler_map:
                        handler = handler_map[reminder.handler_id]
                    else:
                        handler = reminder.handler
                        handler_map[reminder.handler_id] = handler
                    reminder.error = False
                    reminder.error_msg = None
                    handler.set_next_fire(reminder, current_timestamp)
                    reminder.save(**kwargs)
        
        timezone = report_utils.get_timezone(request.couch_user.user_id, self.domain)
        reminders = []
        for reminder in CaseReminder.view("reminders/reminders_in_error",
                startkey=[self.domain], endkey=[self.domain, {}], include_docs=True).all():
            if reminder.handler_id in handler_map:
                handler = handler_map[reminder.handler_id]
            else:
                handler = reminder.handler
                handler_map[reminder.handler_id] = handler
            recipient = reminder.recipient
            case = reminder.case
            reminders.append({
                "reminder_id": reminder._id,
                "handler_id": reminder.handler_id,
                "handler_name": handler.nickname,
                "case_id": case.get_id if case is not None else None,
                "case_name": case.name if case is not None else None,
                "next_fire": tz_utils.adjust_datetime_to_timezone(reminder.next_fire, pytz.utc.zone, timezone.zone).strftime("%Y-%m-%d %H:%M:%S"),
                "error_msg": reminder.error_msg,
                "recipient_name": get_recipient_name(recipient),
            })
        return {
            "show_time_notice": True,
            "domain": self.domain,
            "reminders": reminders,
            "timezone": timezone,
            "timezone_now": datetime.now(tz=timezone),
        }
