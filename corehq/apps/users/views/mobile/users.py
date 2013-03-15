import json
import csv
import io
import uuid
from django.utils.safestring import mark_safe

from openpyxl.shared.exc import InvalidFileException
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse,\
    HttpResponseForbidden, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST
from django.contrib import messages

from couchexport.models import Format
from corehq.apps.users.forms import CommCareAccountForm
from corehq.apps.users.models import CommCareUser
from corehq.apps.groups.models import Group
from corehq.apps.users.bulkupload import create_or_update_users_and_groups,\
    check_headers, dump_users_and_groups, GroupNameError
from corehq.apps.users.tasks import bulk_upload_async
from corehq.apps.users.views import (require_can_edit_commcare_users, account as users_account, BaseUserSettingsView)
from dimagi.utils.decorators.memoized import memoized
from dimagi.utils.html import format_html
from dimagi.utils.decorators.view import get_file
from dimagi.utils.excel import WorkbookJSONReader, WorksheetNotFound


DEFAULT_USER_LIST_LIMIT = 10


def account(*args, **kwargs):
    return users_account(*args, **kwargs)


class BaseMobileWorkersView(BaseUserSettingsView):

    @method_decorator(require_can_edit_commcare_users)
    def dispatch(self, request, *args, **kwargs):
        return super(BaseMobileWorkersView, self).dispatch(request, *args, **kwargs)


class DefaultMobileWorkersView(BaseMobileWorkersView):
    """
        Sets up the structure to render the mobile workers page.
    """
    name = "commcare_users"
    page_name = "Mobile Workers"
    template_name = "users/mobile/users_list.html"

    @property
    @memoized
    def page(self):
        return int(self.request.GET.get('page', 1))

    @property
    @memoized
    def limit(self):
        return int(self.request.GET.get('limit', DEFAULT_USER_LIST_LIMIT))

    @property
    @memoized
    def more_columns(self):
        return json.loads(self.request.GET.get('more_columns', 'false'))

    @property
    @memoized
    def cannot_share(self):
        return json.loads(self.request.GET.get('cannot_share', 'false'))

    @property
    @memoized
    def show_inactive(self):
        return json.loads(self.request.GET.get('show_inactive', 'false'))

    @property
    @memoized
    def total(self):
        return CommCareUser.total_by_domain(self.domain, is_active=not self.show_inactive)

    @property
    def page_context(self):
        return {
            'users_list': {
                'page': self.page,
                'limit': self.limit,
                'total': self.total,
            },
            'cannot_share': self.cannot_share,
            'show_inactive': self.show_inactive,
            'more_columns': self.more_columns,
            'show_case_sharing': self.request.project.case_sharing_included(),
            'pagination_limit_options': range(DEFAULT_USER_LIST_LIMIT, 51, DEFAULT_USER_LIST_LIMIT),
        }


class UserListJSONView(DefaultMobileWorkersView):
    """
        Paginates through the mobile workers list.
    """
    name = "user_list"

    @property
    @memoized
    def sort_by(self):
        return self.request.GET.get('sortBy', 'abc')

    @property
    @memoized
    def users_list(self):
        skip = (self.page - 1) * self.limit
        if self.cannot_share:
            users = CommCareUser.cannot_share(self.domain, limit=self.limit, skip=skip)
        else:
            users = CommCareUser.by_domain(self.domain, is_active=not self.show_inactive, limit=self.limit, skip=skip)

        if self.sort_by == 'forms':
            users.sort(key=lambda user: -user.form_count)

        users_list = []
        for user in users:
            user_data = {
                'user_id': user.user_id,
                'status': "" if user.is_active else "Archived",
                'edit_url': reverse('commcare_user_account', args=[self.domain, user.user_id]),
                'username': user.raw_username,
                'full_name': user.full_name,
                'joined_on': user.date_joined.strftime("%d %b %Y"),
                'phone_numbers': user.phone_numbers,
                'form_count': "--",
                'case_count': "--",
                'case_sharing_groups': [],
            }
            if self.more_columns:
                user_data.update({
                    'form_count': user.form_count,
                    'case_count': user.case_count,
                })
                if self.request.project.case_sharing_included():
                    user_data.update({
                        'case_sharing_groups': [g.name for g in user.get_case_sharing_groups()]
                    })
            if self.request.couch_user.can_edit_commcare_user:
                if user.is_active:
                    archive_action_desc = ("As a result of archiving, this user will no longer "
                                           "appear in reports. This action is reversable; you can "
                                           "reactivate this user by viewing Show Archived Mobile Workers and "
                                           "clicking 'Unarchive'.")
                else:
                    archive_action_desc = "This will re-activate the user, and the user will show up in reports again."
                user_data.update({
                    'archive_action_text': "Archive" if user.is_active else "Un-Archive",
                    'archive_action_url': reverse('%s_commcare_user' % ('archive' if user.is_active else 'unarchive'),
                                                  args=[self.domain, user.user_id]),
                    'archive_action_desc': archive_action_desc,
                    'archive_action_complete': False,
                })
            users_list.append(user_data)
        return users_list

    @property
    def page_context(self):
        return {
            'success': True,
            'current_page': self.page,
            'users_list': self.users_list,
        }

    def get_context_data(self, **kwargs):
        return self.page_context

    def render_to_response(self, context, **response_kwargs):
        return HttpResponse(json.dumps(context))


# this was originally written with a GET, which is wrong
# I'm not fixing for now, just adding the require_POST to make it unusable
@require_POST
@require_can_edit_commcare_users
def set_commcare_user_group(request, domain):
    user_id = request.GET.get('user', '')
    user = CommCareUser.get_by_user_id(user_id)
    group_name = request.GET.get('group', '')
    group = Group.by_name(domain, group_name)
    if not user.is_commcare_user() or user.domain != domain or not group:
        return HttpResponseForbidden()
    for group in user.get_case_sharing_groups():
        group.remove_user(user)
    group.add_user(user)
    return HttpResponseRedirect(reverse(DefaultMobileWorkersView.name, args=[domain]))


@require_can_edit_commcare_users
def archive_commcare_user(request, domain, user_id, is_active=False):
    user = CommCareUser.get_by_user_id(user_id, domain)
    user.is_active = is_active
    user.save()
    return HttpResponse(json.dumps(dict(
        success=True,
        message="User '%s' has successfully been %s." %
                (user.raw_username, "Un-Archived" if user.is_active else "Archived")
    )))


@require_can_edit_commcare_users
@require_POST
def delete_commcare_user(request, domain, user_id):
    user = CommCareUser.get_by_user_id(user_id, domain)
    user.retire()
    messages.success(request, "User %s and all their submissions have been permanently deleted" % user.username)
    return HttpResponseRedirect(reverse(DefaultMobileWorkersView.name, args=[domain]))


@require_can_edit_commcare_users
@require_POST
def restore_commcare_user(request, domain, user_id):
    user = CommCareUser.get_by_user_id(user_id, domain)
    user.unretire()
    messages.success(request, "User %s and all their submissions have been restored" % user.username)
    return HttpResponseRedirect(reverse('user_account', args=[domain, user_id]))


@require_can_edit_commcare_users
@require_POST
def update_user_data(request, domain, couch_user_id):
    updated_data = json.loads(request.POST["user-data"])
    user = CommCareUser.get(couch_user_id)
    assert user.doc_type == "CommCareUser"
    assert user.domain == domain
    user.user_data = updated_data
    user.save()
    messages.success(request, "User data updated!")
    return HttpResponseRedirect(reverse('user_account', args=[domain, couch_user_id]))


class AddCommCareAccountView(BaseMobileWorkersView):
    name = "add_commcare_account"
    template_name = "users/add_commcare_account.html"
    page_name = "New Mobile Worker"

    @property
    @memoized
    def form(self):
        if self.request.method == "POST":
            return CommCareAccountForm(self.request.POST)
        return CommCareAccountForm()

    @property
    @memoized
    def page_context(self):
        return {
            'form': self.form,
            'only_numeric': self.request.project.password_format() == 'n',
        }

    def post(self, request, *args, **kwargs):
        self.form.password_format = request.project.password_format()
        if self.form.is_valid():
            username = self.form.cleaned_data["username"]
            password = self.form.cleaned_data["password"]

            couch_user = CommCareUser.create(self.domain, username, password, device_id='Generated from HQ')
            couch_user.save()
            return HttpResponseRedirect(reverse("commcare_user_account", args=[self.domain, couch_user.userID]))
        return self.get(request, *args, **kwargs)


class UploadCommCareUsers(BaseMobileWorkersView):
    name = "upload_commcare_users"
    page_name = "Bulk Upload Mobile Workers"
    template_name = 'users/upload_commcare_users.html'

    @property
    @memoized
    def show_secret(self):
        return self.request.REQUEST.get("secret", False)

    @property
    @memoized
    def page_context(self):
        return {
            'show_secret_settings': self.show_secret,
        }

    @method_decorator(get_file)
    def post(self, request, *args, **kwargs):
        """View's dispatch method automatically calls this"""

        try:
            self.workbook = WorkbookJSONReader(request.file)
        except InvalidFileException:
            try:
                csv.DictReader(io.StringIO(request.file.read().decode('ascii'), newline=None))
                return HttpResponseBadRequest(
                    "CommCare HQ no longer supports CSV upload. "
                    "Please convert to Excel 2007 or higher (.xlsx) and try again."
                )
            except UnicodeDecodeError:
                return HttpResponseBadRequest("Unrecognized format")

        try:
            self.user_specs = self.workbook.get_worksheet(title='users')
        except WorksheetNotFound:
            try:
                self.user_specs = self.workbook.get_worksheet()
            except WorksheetNotFound:
                return HttpResponseBadRequest("Workbook has no worksheets")

        try:
            self.group_specs = self.workbook.get_worksheet(title='groups')
        except KeyError:
            self.group_specs = []

        try:
            check_headers(self.user_specs)
        except Exception, e:
            return HttpResponseBadRequest(e)

        response = HttpResponse()
        response_rows = []
        async = request.REQUEST.get("async", False)
        if async:
            download_id = uuid.uuid4().hex
            bulk_upload_async.delay(download_id, self.domain,
                list(self.user_specs),
                list(self.group_specs))
            messages.success(request,
                'Your upload is in progress. You can check the progress <a href="%s">here</a>.' %\
                reverse('hq_soil_download', kwargs={'domain': self.domain, 'download_id': download_id}),
                extra_tags="html")
        else:
            ret = create_or_update_users_and_groups(self.domain, self.user_specs, self.group_specs)
            for error in ret["errors"]:
                messages.error(request, error)

            for row in ret["rows"]:
                response_rows.append(row)

        redirect = request.POST.get('redirect')
        if redirect:
            if not async:
                messages.success(request, 'Your bulk user upload is complete!')
            problem_rows = []
            for row in response_rows:
                if row['flag'] not in ('updated', 'created'):
                    problem_rows.append(row)
            if problem_rows:
                messages.error(request, 'However, we ran into problems with the following users:')
                for row in problem_rows:
                    if row['flag'] == 'missing-data':
                        messages.error(request, 'A row with no username was skipped')
                    else:
                        messages.error(request, '{username}: {flag}'.format(**row))
            return HttpResponseRedirect(redirect)
        else:
            return response


@require_can_edit_commcare_users
def download_commcare_users(request, domain):
    response = HttpResponse(mimetype=Format.from_format('xlsx').mimetype)
    response['Content-Disposition'] = 'attachment; filename=%s_users.xlsx' % domain

    try:
        dump_users_and_groups(response, domain)
    except GroupNameError as e:
        group_urls = [
            reverse('group_members', args=[domain, group.get_id])
            for group in e.blank_groups
        ]

        def make_link(url, i):
            return format_html(
                '<a href="{}">{}</a>',
                url,
                _('Blank Group %s') % i
            )

        group_links = [
            make_link(url, i + 1)
            for i, url in enumerate(group_urls)
        ]
        msg = format_html(
            _(
                'The following groups have no name. '
                'Please name them before continuing: {}'
            ),
            mark_safe(', '.join(group_links))
        )
        messages.error(request, msg, extra_tags='html')
        return HttpResponseRedirect(
            reverse('upload_commcare_users', args=[domain])
        )

    return response
