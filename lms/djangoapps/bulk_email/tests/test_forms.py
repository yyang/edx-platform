# -*- coding: utf-8 -*-
"""
Unit tests for bulk-email-related forms.
"""
from django.test.utils import override_settings
from django.conf import settings

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory
from courseware.tests.tests import TEST_DATA_MONGO_MODULESTORE
from courseware.tests.modulestore_config import TEST_DATA_MIXED_MODULESTORE

from xmodule.modulestore.django import modulestore
from xmodule.modulestore import ModuleStoreEnum

from mock import patch

from bulk_email.models import CourseAuthorization
from bulk_email.forms import CourseAuthorizationAdminForm
from opaque_keys.edx.locations import SlashSeparatedCourseKey


@override_settings(MODULESTORE=TEST_DATA_MONGO_MODULESTORE)
class CourseAuthorizationFormTest(ModuleStoreTestCase):
    """Test the CourseAuthorizationAdminForm form for Mongo-backed courses."""

    def setUp(self):
        course_title = u"ẗëṡẗ title ｲ乇丂ｲ ﾶ乇丂丂ﾑg乇 ｷo尺 ﾑﾚﾚ тэѕт мэѕѕаБэ"
        self.course = CourseFactory.create(display_name=course_title)

    def tearDown(self):
        """
        Undo all patches.
        """
        patch.stopall()

    @patch.dict(settings.FEATURES, {'ENABLE_INSTRUCTOR_EMAIL': True, 'REQUIRE_COURSE_EMAIL_AUTH': True})
    def test_authorize_mongo_course(self):
        # Initially course shouldn't be authorized
        self.assertFalse(CourseAuthorization.instructor_email_enabled(self.course.id))
        # Test authorizing the course, which should totally work
        form_data = {'course_id': self.course.id.to_deprecated_string(), 'email_enabled': True}
        form = CourseAuthorizationAdminForm(data=form_data)
        # Validation should work
        self.assertTrue(form.is_valid())
        form.save()
        # Check that this course is authorized
        self.assertTrue(CourseAuthorization.instructor_email_enabled(self.course.id))

    @patch.dict(settings.FEATURES, {'ENABLE_INSTRUCTOR_EMAIL': True, 'REQUIRE_COURSE_EMAIL_AUTH': True})
    def test_repeat_course(self):
        # Initially course shouldn't be authorized
        self.assertFalse(CourseAuthorization.instructor_email_enabled(self.course.id))
        # Test authorizing the course, which should totally work
        form_data = {'course_id': self.course.id.to_deprecated_string(), 'email_enabled': True}
        form = CourseAuthorizationAdminForm(data=form_data)
        # Validation should work
        self.assertTrue(form.is_valid())
        form.save()
        # Check that this course is authorized
        self.assertTrue(CourseAuthorization.instructor_email_enabled(self.course.id))

        # Now make a new course authorization with the same course id that tries to turn email off
        form_data = {'course_id': self.course.id.to_deprecated_string(), 'email_enabled': False}
        form = CourseAuthorizationAdminForm(data=form_data)
        # Validation should not work because course_id field is unique
        self.assertFalse(form.is_valid())
        self.assertEquals(
            "Course authorization with this Course id already exists.",
            form._errors['course_id'][0]  # pylint: disable=protected-access
        )
        with self.assertRaisesRegexp(ValueError, "The CourseAuthorization could not be created because the data didn't validate."):
            form.save()

        # Course should still be authorized (invalid attempt had no effect)
        self.assertTrue(CourseAuthorization.instructor_email_enabled(self.course.id))

    @patch.dict(settings.FEATURES, {'ENABLE_INSTRUCTOR_EMAIL': True, 'REQUIRE_COURSE_EMAIL_AUTH': True})
    def test_form_typo(self):
        # Munge course id
        bad_id = SlashSeparatedCourseKey(u'Broken{}'.format(self.course.id.org), 'hello', self.course.id.run + '_typo')

        form_data = {'course_id': bad_id.to_deprecated_string(), 'email_enabled': True}
        form = CourseAuthorizationAdminForm(data=form_data)
        # Validation shouldn't work
        self.assertFalse(form.is_valid())

        msg = u'COURSE NOT FOUND'
        msg += u' --- Entered course id was: "{0}". '.format(bad_id.to_deprecated_string())
        msg += 'Please recheck that you have supplied a valid course id.'
        self.assertEquals(msg, form._errors['course_id'][0])  # pylint: disable=protected-access

        with self.assertRaisesRegexp(ValueError, "The CourseAuthorization could not be created because the data didn't validate."):
            form.save()

    @patch.dict(settings.FEATURES, {'ENABLE_INSTRUCTOR_EMAIL': True, 'REQUIRE_COURSE_EMAIL_AUTH': True})
    def test_form_invalid_key(self):
        form_data = {'course_id': "asd::**!@#$%^&*())//foobar!!", 'email_enabled': True}
        form = CourseAuthorizationAdminForm(data=form_data)
        # Validation shouldn't work
        self.assertFalse(form.is_valid())

        msg = u'Course id invalid.'
        msg += u' --- Entered course id was: "asd::**!@#$%^&*())//foobar!!". '
        msg += 'Please recheck that you have supplied a valid course id.'
        self.assertEquals(msg, form._errors['course_id'][0])  # pylint: disable=protected-access

        with self.assertRaisesRegexp(ValueError, "The CourseAuthorization could not be created because the data didn't validate."):
            form.save()

    @patch.dict(settings.FEATURES, {'ENABLE_INSTRUCTOR_EMAIL': True, 'REQUIRE_COURSE_EMAIL_AUTH': True})
    def test_course_name_only(self):
        # Munge course id - common
        form_data = {'course_id': self.course.id.run, 'email_enabled': True}
        form = CourseAuthorizationAdminForm(data=form_data)
        # Validation shouldn't work
        self.assertFalse(form.is_valid())

        error_msg = form._errors['course_id'][0]
        self.assertIn(u'--- Entered course id was: "{0}". '.format(self.course.id.run), error_msg)
        self.assertIn(u'Please recheck that you have supplied a valid course id.', error_msg)

        with self.assertRaisesRegexp(ValueError, "The CourseAuthorization could not be created because the data didn't validate."):
            form.save()


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class CourseAuthorizationXMLFormTest(ModuleStoreTestCase):
    """Check that XML courses cannot be authorized for email."""

    @patch.dict(settings.FEATURES, {'ENABLE_INSTRUCTOR_EMAIL': True, 'REQUIRE_COURSE_EMAIL_AUTH': True})
    def test_xml_course_authorization(self):
        course_id = SlashSeparatedCourseKey('edX', 'toy', '2012_Fall')
        # Assert this is an XML course
        self.assertEqual(modulestore().get_modulestore_type(course_id), ModuleStoreEnum.Type.xml)

        form_data = {'course_id': course_id.to_deprecated_string(), 'email_enabled': True}
        form = CourseAuthorizationAdminForm(data=form_data)
        # Validation shouldn't work
        self.assertFalse(form.is_valid())

        msg = u"Course Email feature is only available for courses authored in Studio. "
        msg += u'"{0}" appears to be an XML backed course.'.format(course_id.to_deprecated_string())
        self.assertEquals(msg, form._errors['course_id'][0])  # pylint: disable=protected-access

        with self.assertRaisesRegexp(ValueError, "The CourseAuthorization could not be created because the data didn't validate."):
            form.save()
