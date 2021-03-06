import functools
from couchdbkit.ext.django import loading
from couchdbkit.ext.django.testrunner import CouchDbKitTestSuiteRunner
import datetime
from django.conf import settings
from django.utils import unittest
import settingshelper

from django.test import TransactionTestCase
from mock import patch, Mock


class HqTestSuiteRunner(CouchDbKitTestSuiteRunner):
    """
    A test suite runner for Hq.  On top of the couchdb testrunner, also
    apply all our monkeypatches to the settings.

    To use this, change the settings.py file to read:

    TEST_RUNNER = 'Hq.testrunner.HqTestSuiteRunner'
    """

    dbs = []

    def setup_test_environment(self, **kwargs):
        # monkey patch TEST_APPS into INSTALLED_APPS
        # so that tests are run for them
        # without having to explicitly have them in INSTALLED_APPS
        # weird list/tuple type issues, so force everything to tuples
        settings.INSTALLED_APPS = (tuple(settings.INSTALLED_APPS) +
                                   tuple(settings.TEST_APPS))
        settings.CELERY_ALWAYS_EAGER = True
        return super(HqTestSuiteRunner, self).setup_test_environment(**kwargs)

    def setup_databases(self, **kwargs):
        self.newdbname = self.get_test_db_name(settings.COUCH_DATABASE_NAME)
        print "overridding the couch settings!"
        new_db_settings = settingshelper.get_dynamic_db_settings(
            settings.COUCH_SERVER_ROOT,
            settings.COUCH_USERNAME,
            settings.COUCH_PASSWORD,
            self.newdbname,
        )
        settings.COUCH_DATABASE_NAME = self.newdbname
        for (setting, value) in new_db_settings.items():
            setattr(settings, setting, value)
            print "set %s settting to %s" % (setting, value)

        return super(HqTestSuiteRunner, self).setup_databases(**kwargs)

    def filter_test_labels(self, test_labels):
        if not test_labels:
            test_labels = [self._strip(app) for app in settings.INSTALLED_APPS
                           if not app in settings.APPS_TO_EXCLUDE_FROM_TESTS
                           and not app.startswith('django.')]
        return test_labels

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        test_labels = self.filter_test_labels(test_labels)
        return super(HqTestSuiteRunner, self).run_tests(
            test_labels, extra_tests, **kwargs
        )

    def _strip(self, app_name):
        return app_name.split('.')[-1]


class TimingTestSuite(unittest.TestSuite):
    def __init__(self, tests=()):
        super(TimingTestSuite, self).__init__(tests)
        self.test_times = []

    def addTest(self, test):
        suite = self

        class Foo(test.__class__):
            def __call__(self, *args, **kwargs):
                start = datetime.datetime.utcnow()
                result = super(Foo, self).__call__(*args, **kwargs)
                end = datetime.datetime.utcnow()
                suite.test_times.append((self, end - start))
                return result
        Foo.__name__ = test.__class__.__name__
        Foo.__module__ = test.__class__.__module__
        test.__class__ = Foo
        super(TimingTestSuite, self).addTest(test)


class TwoStageTestRunner(HqTestSuiteRunner):
    """
    Test runner which splits testing into two stages:
     - Stage 1 runs all test that don't require DB access (test that don't inherit from TransactionTestCase)
     - Stage 2 runs all DB tests (test that do inherit from TransactionTestCase)

    Based off http://www.caktusgroup.com/blog/2013/10/02/skipping-test-db-creation/
    """

    def build_suite(self, *args, **kwargs):
        """
        Check if any of the tests to run subclasses TransactionTestCase.
        """
        suite = super(TwoStageTestRunner, self).build_suite(*args, **kwargs)
        simple_tests = unittest.TestSuite()
        db_tests = TimingTestSuite()
        for test in suite:
            if isinstance(test, TransactionTestCase):
                db_tests.addTest(test)
            else:
                simple_tests.addTest(test)
        return simple_tests, db_tests

    def setup_mock_database(self):
        """
        Ensure that touching the DB raises and error.
        """
        self._db_patch = patch('django.db.backends.util.CursorWrapper')
        db_mock = self._db_patch.start()
        db_mock.side_effect = RuntimeError('No database present during SimpleTestCase run.')

        mock_couch = Mock(side_effect=RuntimeError('No database present during SimpleTestCase run.'), spec=[])

        # register our dbs with the extension document classes
        old_handler = loading.couchdbkit_handler
        for app, value in old_handler.app_schema.items():
            for name, cls in value.items():
                cls.set_db(mock_couch)

    def teardown_mock_database(self):
        """
        Remove cursor patch.
        """
        self._db_patch.stop()

    def run_non_db_tests(self, suite):
        print("Running {0} tests without database".format(suite.countTestCases()))
        self.setup_mock_database()
        result = self.run_suite(suite)
        self.teardown_mock_database()
        return self.suite_result(suite, result)

    def run_db_tests(self, suite):
        print("Running {0} tests with database".format(suite.countTestCases()))
        old_config = self.setup_databases()
        result = self.run_suite(suite)
        self.teardown_databases(old_config)
        return self.suite_result(suite, result)

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        """
        Run the unit tests in two groups, those that don't need db access
        first and those that require db access afterwards.
        """
        test_labels = self.filter_test_labels(test_labels)
        self.setup_test_environment()
        simple_suite, db_suite = self.build_suite(test_labels, extra_tests)
        failures = 0
        if simple_suite.countTestCases():
            failures += self.run_non_db_tests(simple_suite)

        if db_suite.countTestCases():
            failures += self.run_db_tests(db_suite)
            self.print_test_times(db_suite)
        self.teardown_test_environment()
        return failures

    def print_test_times(self, suite, percent=.5):
        total_time = reduce(
            lambda x, y: x + y,
            (test_time for _, test_time in suite.test_times),
            datetime.timedelta(seconds=0)
        )
        rounded_total_time = total_time - datetime.timedelta(
            microseconds=total_time.microseconds
        )
        cumulative_time = datetime.timedelta(seconds=0)

        print (
            '{:.0f}% of the test time (total: {}) '
            'was spent in the following tests:'.format(
                percent * 100,
                rounded_total_time,
            )
        )
        for test, test_time in sorted(suite.test_times, key=lambda x: x[1], reverse=True):
            cumulative_time += test_time
            print ' ', test, test_time
            if cumulative_time > total_time / 2:
                break


class NonDbOnlyTestRunner(TwoStageTestRunner):
    """
    Override run_db_test to do nothing.
    """
    def run_db_tests(self, suite):
        print("Skipping {0} database tests".format(suite.countTestCases()))
        return 0


class DbOnlyTestRunner(TwoStageTestRunner):
    """
    Override run_non_db_tests to do nothing.
    """
    def run_non_db_tests(self, suite):
        print("Skipping {0} non-database tests".format(suite.countTestCases()))
        return 0


class _OnlySpecificApps(HqTestSuiteRunner):
    app_labels = set()
    # If include is False, then run for all EXCEPT app_labels
    include = True

    def filter_test_labels(self, test_labels):
        if not test_labels:
            test_labels = super(_OnlySpecificApps, self).filter_test_labels(test_labels)
            test_labels = [app_label for app_label in test_labels
                           if self.include == (app_label in self.app_labels)]
            print "Running tests for the following apps:"
            for test_label in sorted(test_labels):
                print "  {}".format(test_label)

        return test_labels


def _bootstrap_group_test_runners():
    """
    Dynamically insert classes named GroupTestRunner[0-N] and GroupTestRunnerCatchall
    generated from the TRAVIS_TEST_GROUPS settings variable
    into this module, so they can be used like
        python manage.py test --testrunner=testrunner.GroupTestRunner0
        python manage.py test --testrunner=testrunner.GroupTestRunner1
        ...
        python manage.py test --testrunner=testrunner.GroupTestRunnerCatchall

    When you change the number of groups in TRAVIS_TEST_GROUPS, you must also
    manually edit travis.yml have the following env variables:

        env:
            [...] TEST_RUNNER=testrunner.NonDbOnlyTestRunner
            [...] TEST_RUNNER=testrunner.GroupTestRunner0
            [...] TEST_RUNNER=testrunner.GroupTestRunner1
            ...
            [...] TEST_RUNNER=testrunner.GroupTestRunnerCatchall

    """
    for i, app_labels in enumerate(settings.TRAVIS_TEST_GROUPS):
        class_name = 'GroupTestRunner{}'.format(i)
        globals()[class_name] = type(
            class_name,
            (_OnlySpecificApps, DbOnlyTestRunner),
            {
                'app_labels': settings.TRAVIS_TEST_GROUPS[i]
            }
        )
    class_name = 'GroupTestRunnerCatchall'
    globals()[class_name] = type(
        class_name,
        (_OnlySpecificApps, DbOnlyTestRunner),
        {
            'app_labels': {app_label
                           for app_labels in settings.TRAVIS_TEST_GROUPS
                           for app_label in app_labels},
            'include': False,
        }
    )

_bootstrap_group_test_runners()
