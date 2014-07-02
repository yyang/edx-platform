"""
Test for export all courses.
"""
import shutil
from tempfile import mkdtemp

from contentstore.management.commands.export_all_courses import export_courses_to_output_path

from xmodule.modulestore import MONGO_MODULESTORE_TYPE
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


class ExportAllCourses(ModuleStoreTestCase):
    """
    Tests exporting all courses.
    """
    def setUp(self):
        """ Common setup. """
        self.store = modulestore()._get_modulestore_by_type(MONGO_MODULESTORE_TYPE)
        self.temp_dir = mkdtemp()
        self.old_course = CourseFactory()

    def test_export_all_courses(self):
        """
        Test exporting good and faulty courses
        """
        course_id = self.old_course.id

        courses, failed_export_courses = export_courses_to_output_path(self.temp_dir)
        self.assertEqual(len(courses), 1)
        self.assertEqual(len(failed_export_courses), 0)

        # manually make course faulty and check that it fails on export
        self.store.collection.update(
            {'_id.org': course_id.org, '_id.course': course_id.course, '_id.name': course_id.run},
            {'$set': {'metadata.tags': 'crash'}}
        )
        courses, failed_export_courses = export_courses_to_output_path(self.temp_dir)
        self.assertEqual(len(courses), 1)
        self.assertEqual(len(failed_export_courses), 1)
        self.assertEqual(failed_export_courses[0], unicode(course_id))

    def tearDown(self):
        """ Common cleanup. """
        shutil.rmtree(self.temp_dir)
