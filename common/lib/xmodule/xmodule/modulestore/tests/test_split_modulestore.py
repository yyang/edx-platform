"""
    Test split modulestore w/o using any django stuff.
"""
import datetime
import unittest
import uuid
from importlib import import_module
from path import path
import re
import random

from xblock.fields import Scope
from xmodule.course_module import CourseDescriptor
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.exceptions import (InsufficientSpecificationError, ItemNotFoundError, VersionConflictError,
            DuplicateItemError, DuplicateCourseError)
from opaque_keys.edx.locator import CourseLocator, BlockUsageLocator, VersionTree, LocalId
from xmodule.modulestore.inheritance import InheritanceMixin
from xmodule.x_module import XModuleMixin
from xmodule.fields import Date, Timedelta
from xmodule.modulestore.split_mongo.split import SplitMongoModuleStore
from xmodule.modulestore.tests.test_modulestore import check_has_course_method


BRANCH_NAME_DRAFT = ModuleStoreEnum.BranchName.draft
BRANCH_NAME_PUBLISHED = ModuleStoreEnum.BranchName.published


class SplitModuleTest(unittest.TestCase):
    '''
    The base set of tests manually populates a db w/ courses which have
    versions. It creates unique collection names and removes them after all
    tests finish.
    '''
    # Snippets of what would be in the django settings envs file
    DOC_STORE_CONFIG = {
        'host': 'localhost',
        'db': 'test_xmodule',
        'collection': 'modulestore{0}'.format(uuid.uuid4().hex[:5]),
    }
    modulestore_options = {
        'default_class': 'xmodule.raw_module.RawDescriptor',
        'fs_root': '',
        'xblock_mixins': (InheritanceMixin, XModuleMixin)
    }

    MODULESTORE = {
        'ENGINE': 'xmodule.modulestore.split_mongo.SplitMongoModuleStore',
        'DOC_STORE_CONFIG': DOC_STORE_CONFIG,
        'OPTIONS': modulestore_options
    }

    # don't create django dependency; so, duplicates common.py in envs
    match = re.search(r'(.*?/common)(?:$|/)', path(__file__))
    COMMON_ROOT = match.group(1)

    modulestore = None

    _date_field = Date()
    _time_delta_field = Timedelta()
    COURSE_CONTENT = {
        "testx.GreekHero": {
            "org": "testx",
            "course": "GreekHero",
            "run": "run",
            "root_block_id": "head12345",
            "user_id": "test@edx.org",
            "fields": {
                "tabs": [
                        {
                            "type": "courseware"
                        },
                        {
                            "type": "course_info",
                            "name": "Course Info"
                        },
                        {
                            "type": "discussion",
                            "name": "Discussion"
                        },
                        {
                            "type": "wiki",
                            "name": "Wiki"
                        }
                    ],
                "start": _date_field.from_json("2013-02-14T05:00"),
                "display_name": "The Ancient Greek Hero",
                "grading_policy": {
                    "GRADER": [
                    {
                        "min_count": 5,
                        "weight": 0.15,
                        "type": "Homework",
                        "drop_count": 1,
                        "short_label": "HWa"
                    },
                    {
                        "short_label": "",
                        "min_count": 2,
                        "type": "Lab",
                        "drop_count": 0,
                        "weight": 0.15
                    },
                    {
                        "short_label": "Midterm",
                        "min_count": 1,
                        "type": "Midterm Exam",
                        "drop_count": 0,
                        "weight": 0.3
                    },
                    {
                        "short_label": "Final",
                        "min_count": 1,
                        "type": "Final Exam",
                        "drop_count": 0,
                        "weight": 0.4
                    }
                    ],
                    "GRADE_CUTOFFS": {
                        "Pass": 0.75
                    },
                },
            },
            "revisions": [{
                "user_id": "testassist@edx.org",
                "update": {
                    "head12345": {
                        "end": _date_field.from_json("2013-04-13T04:30"),
                        "tabs": [
                        {
                            "type": "courseware"
                        },
                        {
                            "type": "course_info",
                            "name": "Course Info"
                        },
                        {
                            "type": "discussion",
                            "name": "Discussion"
                        },
                        {
                            "type": "wiki",
                            "name": "Wiki"
                        },
                        {
                            "type": "static_tab",
                            "name": "Syllabus",
                            "url_slug": "01356a17b5924b17a04b7fc2426a3798"
                        },
                        {
                            "type": "static_tab",
                            "name": "Advice for Students",
                            "url_slug": "57e9991c0d794ff58f7defae3e042e39"
                        }
                        ],
                        "graceperiod": _time_delta_field.from_json("2 hours 0 minutes 0 seconds"),
                        "grading_policy": {
                            "GRADER": [
                                {
                                    "min_count": 5,
                                    "weight": 0.15,
                                    "type": "Homework",
                                    "drop_count": 1,
                                    "short_label": "HWa"
                                },
                                {
                                    "short_label": "",
                                    "min_count": 12,
                                    "type": "Lab",
                                    "drop_count": 2,
                                    "weight": 0.15
                                },
                                {
                                    "short_label": "Midterm",
                                    "min_count": 1,
                                    "type": "Midterm Exam",
                                    "drop_count": 0,
                                    "weight": 0.3
                                },
                                {
                                    "short_label": "Final",
                                    "min_count": 1,
                                    "type": "Final Exam",
                                    "drop_count": 0,
                                    "weight": 0.4
                                }
                            ],
                            "GRADE_CUTOFFS": {
                                "Pass": 0.55
                            }
                        },
                    }}
                },
                {"user_id": "testassist@edx.org",
                 "update":
                    {"head12345": {
                        "end": _date_field.from_json("2013-06-13T04:30"),
                        "grading_policy": {
                            "GRADER": [
                                {
                                    "min_count": 4,
                                    "weight": 0.15,
                                    "type": "Homework",
                                    "drop_count": 2,
                                    "short_label": "HWa"
                                },
                                {
                                    "short_label": "",
                                    "min_count": 12,
                                    "type": "Lab",
                                    "drop_count": 2,
                                    "weight": 0.15
                                },
                                {
                                    "short_label": "Midterm",
                                    "min_count": 1,
                                    "type": "Midterm Exam",
                                    "drop_count": 0,
                                    "weight": 0.3
                                },
                                {
                                    "short_label": "Final",
                                    "min_count": 1,
                                    "type": "Final Exam",
                                    "drop_count": 0,
                                    "weight": 0.4
                                }
                            ],
                            "GRADE_CUTOFFS": {
                                "Pass": 0.45
                            }
                        },
                        "enrollment_start": _date_field.from_json("2013-01-01T05:00"),
                        "enrollment_end": _date_field.from_json("2013-03-02T05:00"),
                        "advertised_start": "Fall 2013",
                    }},
                "create": [
                    {
                        "id": "chapter1",
                        "parent": "head12345",
                        "category": "chapter",
                        "fields": {
                            "display_name": "Hercules"
                        },
                    },
                    {
                        "id": "chapter2",
                        "parent": "head12345",
                        "category": "chapter",
                        "fields": {
                            "display_name": "Hera heckles Hercules"
                        },
                    },
                    {
                        "id": "chapter3",
                        "parent": "head12345",
                        "category": "chapter",
                        "fields": {
                            "display_name": "Hera cuckolds Zeus"
                        },
                    },
                    {
                        "id": "problem1",
                        "parent": "chapter3",
                        "category": "problem",
                        "fields": {
                            "display_name": "Problem 3.1",
                            "graceperiod": "4 hours 0 minutes 0 seconds"
                        },
                    },
                    {
                        "id": "problem3_2",
                        "parent": "chapter3",
                        "category": "problem",
                        "fields": {
                            "display_name": "Problem 3.2"
                        },
                    }
                ]
                },
            ]
        },
        "testx.wonderful": {
            "org": "testx",
            "course": "wonderful",
            "run": "run",
            "root_block_id": "head23456",
            "user_id": "test@edx.org",
            "fields": {
                "tabs": [
                    {
                        "type": "courseware"
                    },
                    {
                        "type": "course_info",
                        "name": "Course Info"
                    },
                    {
                        "type": "discussion",
                        "name": "Discussion"
                    },
                    {
                        "type": "wiki",
                        "name": "Wiki"
                    }
                ],
                "start": _date_field.from_json("2013-02-14T05:00"),
                "display_name": "A wonderful course",
                "grading_policy": {
                    "GRADER": [
                        {
                            "min_count": 14,
                            "weight": 0.25,
                            "type": "Homework",
                            "drop_count": 1,
                            "short_label": "HWa"
                        },
                        {
                            "short_label": "",
                            "min_count": 12,
                            "type": "Lab",
                            "drop_count": 2,
                            "weight": 0.25
                        },
                        {
                            "short_label": "Midterm",
                            "min_count": 1,
                            "type": "Midterm Exam",
                            "drop_count": 0,
                            "weight": 0.2
                        },
                        {
                            "short_label": "Final",
                            "min_count": 1,
                            "type": "Final Exam",
                            "drop_count": 0,
                            "weight": 0.3
                        }
                    ],
                    "GRADE_CUTOFFS": {
                        "Pass": 0.95
                    }
                },
            },
            "revisions": [{
                "user_id": "test@edx.org",
                "update": {
                    "head23456": {
                        "display_name": "The most wonderful course",
                        "grading_policy": {
                            "GRADER": [
                                {
                                    "min_count": 14,
                                    "weight": 0.25,
                                    "type": "Homework",
                                    "drop_count": 1,
                                    "short_label": "HWa"
                                },
                                {
                                    "short_label": "",
                                    "min_count": 12,
                                    "type": "Lab",
                                    "drop_count": 2,
                                    "weight": 0.25
                                },
                                {
                                    "short_label": "Midterm",
                                    "min_count": 1,
                                    "type": "Midterm Exam",
                                    "drop_count": 0,
                                    "weight": 0.2
                                },
                                {
                                    "short_label": "Final",
                                    "min_count": 1,
                                    "type": "Final Exam",
                                    "drop_count": 0,
                                    "weight": 0.3
                                }
                            ],
                            "GRADE_CUTOFFS": {
                                "Pass": 0.45
                            }
                        },
                    }
                }
            }
            ]
        },
        "guestx.contender": {
            "org": "guestx",
            "course": "contender",
            "run": "run",
            "root_block_id": "head345679",
            "user_id": "test@guestx.edu",
            "fields": {
                "tabs": [
                    {
                        "type": "courseware"
                    },
                    {
                        "type": "course_info",
                        "name": "Course Info"
                    },
                    {
                        "type": "discussion",
                        "name": "Discussion"
                    },
                    {
                        "type": "wiki",
                        "name": "Wiki"
                    }
                ],
                "start": _date_field.from_json("2013-03-14T05:00"),
                "display_name": "Yet another contender",
                "grading_policy": {
                    "GRADER": [
                        {
                            "min_count": 4,
                            "weight": 0.25,
                            "type": "Homework",
                            "drop_count": 0,
                            "short_label": "HW"
                        },
                        {
                            "short_label": "Midterm",
                            "min_count": 1,
                            "type": "Midterm Exam",
                            "drop_count": 0,
                            "weight": 0.4
                        },
                        {
                            "short_label": "Final",
                            "min_count": 1,
                            "type": "Final Exam",
                            "drop_count": 0,
                            "weight": 0.35
                        }
                    ],
                    "GRADE_CUTOFFS": {
                        "Pass": 0.25
                    }
                },
            }
        },
    }
    @staticmethod
    def bootstrapDB():
        '''
        Sets up the initial data into the db
        '''
        split_store = modulestore()
        for _course_id, course_spec in SplitModuleTest.COURSE_CONTENT.iteritems():
            course = split_store.create_course(
                course_spec['org'],
                course_spec['course'],
                course_spec['run'],
                course_spec['user_id'],
                fields=course_spec['fields'],
                root_block_id=course_spec['root_block_id']
            )
            for revision in course_spec.get('revisions', []):
                for block_id, fields in revision.get('update', {}).iteritems():
                    # cheat since course is most frequent
                    if course.location.block_id == block_id:
                        block = course
                    else:
                        # not easy to figure out the category but get_item won't care
                        block_usage = BlockUsageLocator.make_relative(course.location, '', block_id)
                        block = split_store.get_item(block_usage)
                    for key, value in fields.iteritems():
                        setattr(block, key, value)
                # create new blocks into dag: parent must already exist; thus, order is important
                new_ele_dict = {}
                for spec in revision.get('create', []):
                    if spec['parent'] in new_ele_dict:
                        parent = new_ele_dict.get(spec['parent'])
                    elif spec['parent'] == course.location.block_id:
                        parent = course
                    else:
                        block_usage = BlockUsageLocator.make_relative(course.location, '', spec['parent'])
                        parent = split_store.get_item(block_usage)
                    block_id = LocalId(spec['id'])
                    child = split_store.create_xblock(
                        course.runtime, spec['category'], spec['fields'], block_id, parent_xblock=parent
                    )
                    new_ele_dict[spec['id']] = child
                course = split_store.persist_xblock_dag(course, revision['user_id'])
        # publish "testx.wonderful"
        to_publish = BlockUsageLocator(
            CourseLocator(org="testx", course="wonderful", run="run", branch=BRANCH_NAME_DRAFT),
            block_type='course',
            block_id="head23456"
        )
        destination = CourseLocator(org="testx", course="wonderful", run="run", branch=BRANCH_NAME_PUBLISHED)
        split_store.xblock_publish("test@edx.org", to_publish, destination, [to_publish], None)

    def tearDown(self):
        """
        Clear persistence between each test.
        """
        collection_prefix = SplitModuleTest.MODULESTORE['DOC_STORE_CONFIG']['collection'] + '.'
        if SplitModuleTest.modulestore:
            for collection in ('active_versions', 'structures', 'definitions'):
                modulestore().db.drop_collection(collection_prefix + collection)
            # drop the modulestore to force re init
            SplitModuleTest.modulestore = None
        super(SplitModuleTest, self).tearDown()

    def findByIdInResult(self, collection, _id):
        """
        Result is a collection of descriptors. Find the one whose block id
        matches the _id.
        """
        for element in collection:
            if element.location.block_id == _id:
                return element


class TestHasChildrenAtDepth(SplitModuleTest):
    """Test the has_children_at_depth method of XModuleMixin. """

    def test_has_children_at_depth(self):
        course_locator = CourseLocator(
            org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT
        )
        block_locator = BlockUsageLocator(
            course_locator, 'course', 'head12345'
        )
        block = modulestore().get_item(block_locator)

        self.assertRaises(
            ValueError, block.has_children_at_depth, -1,
        )
        self.assertTrue(block.has_children_at_depth(0))
        self.assertTrue(block.has_children_at_depth(1))
        self.assertFalse(block.has_children_at_depth(2))

        ch1 = modulestore().get_item(
            BlockUsageLocator(course_locator, 'chapter', block_id='chapter1')
        )
        self.assertFalse(ch1.has_children_at_depth(0))

        ch2 = modulestore().get_item(
            BlockUsageLocator(course_locator, 'chapter', block_id='chapter2')
        )
        self.assertFalse(ch2.has_children_at_depth(0))

        ch3 = modulestore().get_item(
            BlockUsageLocator(course_locator, 'chapter', block_id='chapter3')
        )
        self.assertTrue(ch3.has_children_at_depth(0))
        self.assertFalse(ch3.has_children_at_depth(1))


class SplitModuleCourseTests(SplitModuleTest):
    '''
    Course CRUD operation tests
    '''

    def test_get_courses(self):
        courses = modulestore().get_courses(branch=BRANCH_NAME_DRAFT)
        # should have gotten 3 draft courses
        self.assertEqual(len(courses), 3, "Wrong number of courses")
        # check metadata -- NOTE no promised order
        course = self.findByIdInResult(courses, "head12345")
        self.assertEqual(course.location.org, "testx")
        self.assertEqual(course.category, 'course', 'wrong category')
        self.assertEqual(len(course.tabs), 6, "wrong number of tabs")
        self.assertEqual(
            course.display_name, "The Ancient Greek Hero",
            "wrong display name"
        )
        self.assertEqual(
            course.advertised_start, "Fall 2013",
            "advertised_start"
        )
        self.assertEqual(len(course.children), 3, "children")
        # check dates and graders--forces loading of descriptor
        self.assertEqual(course.edited_by, "testassist@edx.org")
        self.assertDictEqual(course.grade_cutoffs, {"Pass": 0.45})

    def test_branch_requests(self):
        # query w/ branch qualifier (both draft and published)
        def _verify_published_course(courses_published):
            """ Helper function for verifying published course. """
            self.assertEqual(len(courses_published), 1, len(courses_published))
            course = self.findByIdInResult(courses_published, "head23456")
            self.assertIsNotNone(course, "published courses")
            self.assertEqual(course.location.course_key.org, "testx")
            self.assertEqual(course.location.course_key.course, "wonderful")
            self.assertEqual(course.category, 'course', 'wrong category')
            self.assertEqual(len(course.tabs), 4, "wrong number of tabs")
            self.assertEqual(course.display_name, "The most wonderful course",
                             course.display_name)
            self.assertIsNone(course.advertised_start)
            self.assertEqual(len(course.children), 0,
                             "children")

        _verify_published_course(modulestore().get_courses(branch=BRANCH_NAME_PUBLISHED))

    def test_search_qualifiers(self):
        # query w/ search criteria
        courses = modulestore().get_courses(branch=BRANCH_NAME_DRAFT, qualifiers={'org': 'testx'})
        self.assertEqual(len(courses), 2)
        self.assertIsNotNone(self.findByIdInResult(courses, "head12345"))
        self.assertIsNotNone(self.findByIdInResult(courses, "head23456"))

    def test_has_course(self):
        '''
        Test the various calling forms for has_course
        '''

        check_has_course_method(
            modulestore(),
            CourseLocator(org='testx', course='wonderful', run="run", branch=BRANCH_NAME_DRAFT),
            locator_key_fields=['org', 'course', 'run']
        )

    def test_get_course(self):
        '''
        Test the various calling forms for get_course
        '''
        locator = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT)
        head_course = modulestore().get_course(locator)
        self.assertNotEqual(head_course.location.version_guid, head_course.previous_version)
        locator = CourseLocator(version_guid=head_course.previous_version)
        course = modulestore().get_course(locator)
        self.assertIsNone(course.location.course_key.org)
        self.assertEqual(course.location.version_guid, head_course.previous_version)
        self.assertEqual(course.category, 'course')
        self.assertEqual(len(course.tabs), 6)
        self.assertEqual(course.display_name, "The Ancient Greek Hero")
        self.assertEqual(course.graceperiod, datetime.timedelta(hours=2))
        self.assertIsNone(course.advertised_start)
        self.assertEqual(len(course.children), 0)
        self.assertNotEqual(course.definition_locator.definition_id, head_course.definition_locator.definition_id)
        # check dates and graders--forces loading of descriptor
        self.assertEqual(course.edited_by, "testassist@edx.org")
        self.assertDictEqual(course.grade_cutoffs, {"Pass": 0.55})

        locator = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT)
        course = modulestore().get_course(locator)
        self.assertEqual(course.location.course_key.org, "testx")
        self.assertEqual(course.location.course_key.course, "GreekHero")
        self.assertEqual(course.location.course_key.run, "run")
        self.assertEqual(course.category, 'course')
        self.assertEqual(len(course.tabs), 6)
        self.assertEqual(course.display_name, "The Ancient Greek Hero")
        self.assertEqual(course.advertised_start, "Fall 2013")
        self.assertEqual(len(course.children), 3)
        # check dates and graders--forces loading of descriptor
        self.assertEqual(course.edited_by, "testassist@edx.org")
        self.assertDictEqual(course.grade_cutoffs, {"Pass": 0.45})

        locator = CourseLocator(org='testx', course='wonderful', run="run", branch=BRANCH_NAME_PUBLISHED)
        course = modulestore().get_course(locator)
        published_version = course.location.version_guid

        locator = CourseLocator(org='testx', course='wonderful', run="run", branch=BRANCH_NAME_DRAFT)
        course = modulestore().get_course(locator)
        self.assertNotEqual(course.location.version_guid, published_version)

    def test_get_course_negative(self):
        # Now negative testing
        with self.assertRaises(InsufficientSpecificationError):
            modulestore().get_course(CourseLocator(org='edu', course='meh', run='blah'))
        with self.assertRaises(ItemNotFoundError):
            modulestore().get_course(CourseLocator(org='edu', course='nosuchthing', run="run", branch=BRANCH_NAME_DRAFT))
        with self.assertRaises(ItemNotFoundError):
            modulestore().get_course(CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_PUBLISHED))

    def test_cache(self):
        """
        Test that the mechanics of caching work.
        """
        locator = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT)
        course = modulestore().get_course(locator)
        block_map = modulestore().cache_items(
            course.system, [child.block_id for child in course.children], course.id, depth=3
        )
        self.assertIn('chapter1', block_map)
        self.assertIn('problem3_2', block_map)

    def test_course_successors(self):
        """
        get_course_successors(course_locator, version_history_depth=1)
        """
        locator = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT)
        course = modulestore().get_course(locator)
        versions = [course.location.version_guid, course.previous_version]
        locator = CourseLocator(version_guid=course.previous_version)
        course = modulestore().get_course(locator)
        versions.append(course.previous_version)

        locator = CourseLocator(version_guid=course.previous_version)
        result = modulestore().get_course_successors(locator)
        self.assertIsInstance(result, VersionTree)
        self.assertIsNone(result.locator.org)
        self.assertEqual(result.locator.version_guid, versions[-1])
        self.assertEqual(len(result.children), 1)
        self.assertEqual(result.children[0].locator.version_guid, versions[-2])
        self.assertEqual(len(result.children[0].children), 0, "descended more than one level")

        result = modulestore().get_course_successors(locator, version_history_depth=2)
        self.assertEqual(len(result.children), 1)
        self.assertEqual(result.children[0].locator.version_guid, versions[-2])
        self.assertEqual(len(result.children[0].children), 1)

        result = modulestore().get_course_successors(locator, version_history_depth=99)
        self.assertEqual(len(result.children), 1)
        self.assertEqual(result.children[0].locator.version_guid, versions[-2])
        self.assertEqual(len(result.children[0].children), 1)
        self.assertEqual(result.children[0].children[0].locator.version_guid, versions[0])

class SplitModuleItemTests(SplitModuleTest):
    '''
    Item read tests including inheritance
    '''

    def test_has_item(self):
        '''
        has_item(BlockUsageLocator)
        '''
        org = 'testx'
        course = 'GreekHero'
        run = 'run'
        course_locator = CourseLocator(org=org, course=course, run=run, branch=BRANCH_NAME_DRAFT)
        course = modulestore().get_course(course_locator)
        previous_version = course.previous_version
        # positive tests of various forms
        locator = course.location.map_into_course(CourseLocator(version_guid=previous_version))
        self.assertTrue(
            modulestore().has_item(locator), "couldn't find in %s" % previous_version
        )

        locator = course.location.version_agnostic()
        self.assertTrue(
            modulestore().has_item(locator),
        )
        self.assertFalse(
            modulestore().has_item(
                BlockUsageLocator(
                    locator.course_key.for_branch(BRANCH_NAME_PUBLISHED),
                    block_type=locator.block_type,
                    block_id=locator.block_id
                )
            ),
            "found in published head"
        )

        # not a course obj
        locator = BlockUsageLocator(course_locator, block_type='chapter', block_id='chapter1')
        self.assertTrue(
            modulestore().has_item(locator),
            "couldn't find chapter1"
        )

        # in published course
        locator = BlockUsageLocator(
            CourseLocator(org="testx", course="wonderful", run="run", branch=BRANCH_NAME_DRAFT),
            block_type="course",
            block_id="head23456"
        )
        self.assertTrue(
            modulestore().has_item(locator.for_branch(BRANCH_NAME_PUBLISHED))
        )

    def test_negative_has_item(self):
        # negative tests--not found
        # no such course or block
        locator = BlockUsageLocator(
            CourseLocator(org="foo", course="doesnotexist", run="run", branch=BRANCH_NAME_DRAFT),
            block_type="course",
            block_id="head23456"
        )
        self.assertFalse(modulestore().has_item(locator))
        locator = BlockUsageLocator(
            CourseLocator(org="testx", course="wonderful", run="run", branch=BRANCH_NAME_DRAFT),
            block_type="vertical",
            block_id="doesnotexist"
        )
        self.assertFalse(modulestore().has_item(locator))

    def test_get_item(self):
        '''
        get_item(blocklocator)
        '''
        hero_locator = CourseLocator(org="testx", course="GreekHero", run="run", branch=BRANCH_NAME_DRAFT)
        course = modulestore().get_course(hero_locator)
        previous_version = course.previous_version

        # positive tests of various forms
        locator = course.location.map_into_course(CourseLocator(version_guid=previous_version))
        block = modulestore().get_item(locator)
        self.assertIsInstance(block, CourseDescriptor)
        self.assertIsInstance(modulestore().get_item(locator), CourseDescriptor)

        def verify_greek_hero(block):
            """
            Check contents of block
            """
            self.assertEqual(block.location.org, "testx")
            self.assertEqual(block.location.course, "GreekHero")
            self.assertEqual(block.location.run, "run")
            self.assertEqual(len(block.tabs), 6, "wrong number of tabs")
            self.assertEqual(block.display_name, "The Ancient Greek Hero")
            self.assertEqual(block.advertised_start, "Fall 2013")
            self.assertEqual(len(block.children), 3)
            # check dates and graders--forces loading of descriptor
            self.assertEqual(block.edited_by, "testassist@edx.org")
            self.assertDictEqual(
                block.grade_cutoffs, {"Pass": 0.45},
            )

        verify_greek_hero(modulestore().get_item(course.location))

        # try to look up other branches
        with self.assertRaises(ItemNotFoundError):
            modulestore().get_item(course.location.for_branch(BRANCH_NAME_PUBLISHED))

    def test_has_changes(self):
        """
        Tests that has_changes() only returns true when changes are present
        """
        draft_course = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT)
        published_course = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_PUBLISHED)
        head = draft_course.make_usage_key('course', 'head12345')
        dummy_user = 'testUser'

        # Not yet published, so changes are present
        self.assertTrue(modulestore().has_changes(head))

        # Publish and verify that there are no unpublished changes
        modulestore().xblock_publish(dummy_user, draft_course, published_course, [head], None)
        self.assertFalse(modulestore().has_changes(head))

        # Change the course, then check that there now are changes
        course = modulestore().get_item(head)
        course.show_calculator = not course.show_calculator
        modulestore().update_item(course, dummy_user)
        self.assertTrue(modulestore().has_changes(head))

        # Publish and verify again
        modulestore().xblock_publish(dummy_user, draft_course, published_course, [head], None)
        self.assertFalse(modulestore().has_changes(head))

    def test_get_non_root(self):
        # not a course obj
        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT), 'chapter', 'chapter1'
        )
        block = modulestore().get_item(locator)
        self.assertEqual(block.location.org, "testx")
        self.assertEqual(block.location.course, "GreekHero")
        self.assertEqual(block.category, 'chapter')
        self.assertEqual(block.display_name, "Hercules")
        self.assertEqual(block.edited_by, "testassist@edx.org")

        # in published course
        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='wonderful', run="run", branch=BRANCH_NAME_PUBLISHED), 'course', 'head23456'
        )
        self.assertIsInstance(
            modulestore().get_item(locator),
            CourseDescriptor
        )

        # negative tests--not found
        # no such course or block
        locator = BlockUsageLocator(
            CourseLocator(org='doesnotexist', course='doesnotexist', run="run", branch=BRANCH_NAME_DRAFT), 'course', 'head23456'
        )
        with self.assertRaises(ItemNotFoundError):
            modulestore().get_item(locator)
        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='wonderful', run="run", branch=BRANCH_NAME_DRAFT), 'html', 'doesnotexist'
        )
        with self.assertRaises(ItemNotFoundError):
            modulestore().get_item(locator)

    # pylint: disable=W0212
    def test_matching(self):
        '''
        test the block and value matches help functions
        '''
        self.assertTrue(modulestore()._value_matches('help', 'help'))
        self.assertFalse(modulestore()._value_matches('help', 'Help'))
        self.assertTrue(modulestore()._value_matches(['distract', 'help', 'notme'], 'help'))
        self.assertFalse(modulestore()._value_matches(['distract', 'Help', 'notme'], 'help'))
        self.assertFalse(modulestore()._block_matches({'field': ['distract', 'Help', 'notme']}, {'field': 'help'}))
        self.assertTrue(modulestore()._block_matches(
            {'field': ['distract', 'help', 'notme'],
                'irrelevant': 2},
            {'field': 'help'}))
        self.assertTrue(modulestore()._value_matches('I need some help', re.compile(r'help')))
        self.assertTrue(modulestore()._value_matches(['I need some help', 'today'], re.compile(r'help')))
        self.assertFalse(modulestore()._value_matches('I need some help', re.compile(r'Help')))
        self.assertTrue(modulestore()._value_matches(['I need some help', 'today'], re.compile(r'Help', re.IGNORECASE)))

        self.assertTrue(modulestore()._block_matches({'a': 1, 'b': 2}, {'a': 1}))
        self.assertFalse(modulestore()._block_matches({'a': 1, 'b': 2}, {'a': 2}))
        self.assertFalse(modulestore()._block_matches({'a': 1, 'b': 2}, {'c': 1}))
        self.assertFalse(modulestore()._block_matches({'a': 1, 'b': 2}, {'a': 1, 'c': 1}))
        self.assertTrue(modulestore()._block_matches({'a': 1, 'b': 2}, {'a': lambda i: 0 < i < 2}))

    def test_get_items(self):
        '''
        get_items(locator, qualifiers, [branch])
        '''
        locator = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT)
        # get all modules
        matches = modulestore().get_items(locator)
        self.assertEqual(len(matches), 6)
        matches = modulestore().get_items(locator)
        self.assertEqual(len(matches), 6)
        matches = modulestore().get_items(locator, category='chapter')
        self.assertEqual(len(matches), 3)
        matches = modulestore().get_items(locator, category='garbage')
        self.assertEqual(len(matches), 0)
        matches = modulestore().get_items(
            locator,
            category='chapter',
            settings={'display_name': re.compile(r'Hera')},
        )
        self.assertEqual(len(matches), 2)

        matches = modulestore().get_items(locator, children='chapter2')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].location.block_id, 'head12345')

    def test_get_parents(self):
        '''
        get_parent_location(locator): BlockUsageLocator
        '''
        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT),
            'chapter', block_id='chapter1'
        )
        parent = modulestore().get_parent_location(locator)
        self.assertIsNotNone(parent)
        self.assertEqual(parent.block_id, 'head12345')
        self.assertEqual(parent.org, "testx")
        self.assertEqual(parent.course, "GreekHero")
        locator = locator.course_key.make_usage_key('Chapter', 'chapter2')
        parent = modulestore().get_parent_location(locator)
        self.assertEqual(parent.block_id, 'head12345')
        locator = locator.course_key.make_usage_key('garbage', 'nosuchblock')
        parent = modulestore().get_parent_location(locator)
        self.assertIsNone(parent)

    def test_get_children(self):
        """
        Test the existing get_children method on xdescriptors
        """
        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT), 'course', 'head12345'
        )
        block = modulestore().get_item(locator)
        children = block.get_children()
        expected_ids = [
            "chapter1", "chapter2", "chapter3"
        ]
        for child in children:
            self.assertEqual(child.category, "chapter")
            self.assertIn(child.location.block_id, expected_ids)
            expected_ids.remove(child.location.block_id)
        self.assertEqual(len(expected_ids), 0)


def version_agnostic(children):
    return [child.version_agnostic() for child in children]


class TestItemCrud(SplitModuleTest):
    """
    Test create update and delete of items
    """
    # DHM do I need to test this case which I believe won't work:
    #  1) fetch a course and some of its blocks
    #  2) do a series of CRUD operations on those previously fetched elements
    # The problem here will be that the version_guid of the items will be the version at time of fetch.
    # Each separate save will change the head version; so, the 2nd piecemeal change will flag the version
    # conflict. That is, if versions are v0..vn and start as v0 in initial fetch, the first CRUD op will
    # say it's changing an object from v0, splitMongo will process it and make the current head v1, the next
    # crud op will pass in its v0 element and splitMongo will flag the version conflict.
    # What I don't know is how realistic this test is and whether to wrap the modulestore with a higher level
    # transactional operation which manages the version change or make the threading cache reason out whether or
    # not the changes are independent and additive and thus non-conflicting.
    # A use case I expect is
    # (client) change this metadata
    # (server) done, here's the new info which, btw, updates the course version to v1
    # (client) add these children to this other node (which says it came from v0 or
    #          will the client have refreshed the version before doing the op?)
    # In this case, having a server side transactional model won't help b/c the bug is a long-transaction on the
    # on the client where it would be a mistake for the server to assume anything about client consistency. The best
    # the server could do would be to see if the parent's children changed at all since v0.

    def test_create_minimal_item(self):
        """
        create_item(course_or_parent_locator, category, user, definition_locator=None, fields): new_desciptor
        """
        # grab link to course to ensure new versioning works
        locator = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT)
        premod_course = modulestore().get_course(locator)
        premod_history = modulestore().get_course_history_info(premod_course.location)
        # add minimal one w/o a parent
        category = 'sequential'
        new_module = modulestore().create_item(
            locator, category, 'user123',
            fields={'display_name': 'new sequential'}
        )
        # check that course version changed and course's previous is the other one
        self.assertEqual(new_module.location.course, "GreekHero")
        self.assertNotEqual(new_module.location.version_guid, premod_course.location.version_guid)
        self.assertIsNone(locator.version_guid, "Version inadvertently filled in")
        current_course = modulestore().get_course(locator)
        self.assertEqual(new_module.location.version_guid, current_course.location.version_guid)

        history_info = modulestore().get_course_history_info(current_course.location)
        self.assertEqual(history_info['previous_version'], premod_course.location.version_guid)
        self.assertEqual(history_info['original_version'], premod_history['original_version'])
        self.assertEqual(history_info['edited_by'], "user123")
        # check block's info: category, definition_locator, and display_name
        self.assertEqual(new_module.category, 'sequential')
        self.assertIsNotNone(new_module.definition_locator)
        self.assertEqual(new_module.display_name, 'new sequential')
        # check that block does not exist in previous version
        locator = new_module.location.map_into_course(
            CourseLocator(version_guid=premod_course.location.version_guid)
        )
        with self.assertRaises(ItemNotFoundError):
            modulestore().get_item(locator)

    def test_create_parented_item(self):
        """
        Test create_item w/ specifying the parent of the new item
        """
        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT),
            'chapter', block_id='chapter2'
        )
        original = modulestore().get_item(locator)

        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='wonderful', run="run", branch=BRANCH_NAME_DRAFT), 'course', 'head23456'
        )
        premod_course = modulestore().get_course(locator.course_key)
        category = 'chapter'
        new_module = modulestore().create_item(
            locator, category, 'user123',
            fields={'display_name': 'new chapter'},
            definition_locator=original.definition_locator
        )
        # check that course version changed and course's previous is the other one
        self.assertNotEqual(new_module.location.version_guid, premod_course.location.version_guid)
        parent = modulestore().get_item(locator)
        self.assertIn(new_module.location.version_agnostic(), version_agnostic(parent.children))
        self.assertEqual(new_module.definition_locator.definition_id, original.definition_locator.definition_id)


    def test_unique_naming(self):
        """
        Check that 2 modules of same type get unique block_ids. Also check that if creation provides
        a definition id and new def data that it branches the definition in the db.
        Actually, this tries to test all create_item features not tested above.
        """
        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT),
            'problem', block_id='problem1'
        )
        original = modulestore().get_item(locator)

        locator = BlockUsageLocator(
            CourseLocator(org='guestx', course='contender', run="run", branch=BRANCH_NAME_DRAFT), 'course', 'head345679'
        )
        category = 'problem'
        new_payload = "<problem>empty</problem>"
        new_module = modulestore().create_item(
            locator, category, 'anotheruser',
            fields={'display_name': 'problem 1', 'data': new_payload},
        )
        another_payload = "<problem>not empty</problem>"
        another_module = modulestore().create_item(
            locator, category, 'anotheruser',
            fields={'display_name': 'problem 2', 'data': another_payload},
            definition_locator=original.definition_locator,
        )
        # check that course version changed and course's previous is the other one
        parent = modulestore().get_item(locator)
        self.assertNotEqual(new_module.location.block_id, another_module.location.block_id)
        self.assertIn(new_module.location.version_agnostic(), version_agnostic(parent.children))
        self.assertIn(another_module.location.version_agnostic(), version_agnostic(parent.children))
        self.assertEqual(new_module.data, new_payload)
        self.assertEqual(another_module.data, another_payload)
        # check definition histories
        new_history = modulestore().get_definition_history_info(new_module.definition_locator)
        self.assertIsNone(new_history['previous_version'])
        self.assertEqual(new_history['original_version'], new_module.definition_locator.definition_id)
        self.assertEqual(new_history['edited_by'], "anotheruser")
        another_history = modulestore().get_definition_history_info(another_module.definition_locator)
        self.assertEqual(another_history['previous_version'], original.definition_locator.definition_id)

    def test_encoded_naming(self):
        """
        Check that using odd characters in block id don't break ability to add and retrieve block.
        """
        course_key = CourseLocator(org='guestx', course='contender', run="run", branch=BRANCH_NAME_DRAFT)
        parent_locator = BlockUsageLocator(course_key, 'course', block_id="head345679")
        chapter_locator = BlockUsageLocator(course_key, 'chapter', block_id="foo.bar_-~:0")
        modulestore().create_item(
            parent_locator, 'chapter', 'anotheruser',
            block_id=chapter_locator.block_id,
            fields={'display_name': 'chapter 99'},
        )
        # check that course version changed and course's previous is the other one
        new_module = modulestore().get_item(chapter_locator)
        self.assertEqual(new_module.location.block_id, "foo.bar_-~:0")  # hardcode to ensure BUL init didn't change
        # now try making that a parent of something
        new_payload = "<problem>empty</problem>"
        problem_locator = BlockUsageLocator(course_key, 'problem', block_id="prob.bar_-~:99a")
        modulestore().create_item(
            chapter_locator, 'problem', 'anotheruser',
            block_id=problem_locator.block_id,
            fields={'display_name': 'chapter 99', 'data': new_payload},
        )
        # check that course version changed and course's previous is the other one
        new_module = modulestore().get_item(problem_locator)
        self.assertEqual(new_module.location.block_id, problem_locator.block_id)
        chapter = modulestore().get_item(chapter_locator)
        self.assertIn(problem_locator, version_agnostic(chapter.children))

    def test_create_continue_version(self):
        """
        Test create_item using the continue_version flag
        """
        # start transaction w/ simple creation
        user = random.getrandbits(32)
        new_course = modulestore().create_course('test_org', 'test_transaction', 'test_run', user)
        new_course_locator = new_course.id
        index_history_info = modulestore().get_course_history_info(new_course.location)
        course_block_prev_version = new_course.previous_version
        course_block_update_version = new_course.update_version
        self.assertIsNotNone(new_course_locator.version_guid, "Want to test a definite version")
        versionless_course_locator = new_course_locator.version_agnostic()

        # positive simple case: no force, add chapter
        new_ele = modulestore().create_item(
            new_course.location, 'chapter', user,
            fields={'display_name': 'chapter 1'},
            continue_version=True
        )
        # version info shouldn't change
        self.assertEqual(new_ele.update_version, course_block_update_version)
        self.assertEqual(new_ele.update_version, new_ele.location.version_guid)
        refetch_course = modulestore().get_course(versionless_course_locator)
        self.assertEqual(refetch_course.location.version_guid, new_course.location.version_guid)
        self.assertEqual(refetch_course.previous_version, course_block_prev_version)
        self.assertEqual(refetch_course.update_version, course_block_update_version)
        refetch_index_history_info = modulestore().get_course_history_info(refetch_course.location)
        self.assertEqual(refetch_index_history_info, index_history_info)
        self.assertIn(new_ele.location.version_agnostic(), version_agnostic(refetch_course.children))

        # try to create existing item
        with self.assertRaises(DuplicateItemError):
            _fail = modulestore().create_item(
                new_course.location, 'chapter', user,
                block_id=new_ele.location.block_id,
                fields={'display_name': 'chapter 2'},
                continue_version=True
            )

        # start a new transaction
        new_ele = modulestore().create_item(
            new_course.location, 'chapter', user,
            fields={'display_name': 'chapter 2'},
            continue_version=False
        )
        transaction_guid = new_ele.location.version_guid
        # ensure force w/ continue gives exception
        with self.assertRaises(VersionConflictError):
            _fail = modulestore().create_item(
                new_course.location, 'chapter', user,
                fields={'display_name': 'chapter 2'},
                force=True, continue_version=True
            )

        # ensure trying to continue the old one gives exception
        with self.assertRaises(VersionConflictError):
            _fail = modulestore().create_item(
                new_course.location, 'chapter', user,
                fields={'display_name': 'chapter 3'},
                continue_version=True
            )

        # add new child to old parent in continued (leave off version_guid)
        course_module_locator = new_course.location.version_agnostic()
        new_ele = modulestore().create_item(
            course_module_locator, 'chapter', user,
            fields={'display_name': 'chapter 4'},
            continue_version=True
        )
        self.assertNotEqual(new_ele.update_version, course_block_update_version)
        self.assertEqual(new_ele.location.version_guid, transaction_guid)

        # check children, previous_version
        refetch_course = modulestore().get_course(versionless_course_locator)
        self.assertIn(new_ele.location.version_agnostic(), version_agnostic(refetch_course.children))
        self.assertEqual(refetch_course.previous_version, course_block_update_version)
        self.assertEqual(refetch_course.update_version, transaction_guid)

    def test_update_metadata(self):
        """
        test updating an items metadata ensuring the definition doesn't version but the course does if it should
        """
        locator = BlockUsageLocator(
            CourseLocator(org="testx", course="GreekHero", run="run", branch=BRANCH_NAME_DRAFT),
            'problem', block_id="problem3_2"
        )
        problem = modulestore().get_item(locator)
        pre_def_id = problem.definition_locator.definition_id
        pre_version_guid = problem.location.version_guid
        self.assertIsNotNone(pre_def_id)
        self.assertIsNotNone(pre_version_guid)
        self.assertNotEqual(problem.max_attempts, 4, "Invalidates rest of test")

        problem.max_attempts = 4
        problem.save()  # decache above setting into the kvs
        updated_problem = modulestore().update_item(problem, '**replace_user**')
        # check that course version changed and course's previous is the other one
        self.assertEqual(updated_problem.definition_locator.definition_id, pre_def_id)
        self.assertNotEqual(updated_problem.location.version_guid, pre_version_guid)
        self.assertEqual(updated_problem.max_attempts, 4)
        # refetch to ensure original didn't change
        original_location = problem.location.map_into_course(CourseLocator(version_guid=pre_version_guid))
        problem = modulestore().get_item(original_location)
        self.assertNotEqual(problem.max_attempts, 4, "original changed")

        current_course = modulestore().get_course(locator.course_key)
        self.assertEqual(updated_problem.location.version_guid, current_course.location.version_guid)

        history_info = modulestore().get_course_history_info(current_course.location)
        self.assertEqual(history_info['previous_version'], pre_version_guid)
        self.assertEqual(history_info['edited_by'], "**replace_user**")

    def test_update_children(self):
        """
        test updating an item's children ensuring the definition doesn't version but the course does if it should
        """
        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT), 'chapter', 'chapter3'
        )
        block = modulestore().get_item(locator)
        pre_def_id = block.definition_locator.definition_id
        pre_version_guid = block.location.version_guid

        # reorder children
        self.assertGreater(len(block.children), 0, "meaningless test")
        moved_child = block.children.pop()
        block.save()  # decache model changes
        updated_problem = modulestore().update_item(block, '**replace_user**')
        # check that course version changed and course's previous is the other one
        self.assertEqual(updated_problem.definition_locator.definition_id, pre_def_id)
        self.assertNotEqual(updated_problem.location.version_guid, pre_version_guid)
        self.assertEqual(version_agnostic(updated_problem.children), version_agnostic(block.children))
        self.assertNotIn(moved_child, version_agnostic(updated_problem.children))
        locator = locator.course_key.make_usage_key('Chapter', "chapter1")
        other_block = modulestore().get_item(locator)
        other_block.children.append(moved_child)
        other_updated = modulestore().update_item(other_block, '**replace_user**')
        self.assertIn(moved_child.version_agnostic(), version_agnostic(other_updated.children))

    def test_update_definition(self):
        """
        test updating an item's definition: ensure it gets versioned as well as the course getting versioned
        """
        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT), 'course', 'head12345'
        )
        block = modulestore().get_item(locator)
        pre_def_id = block.definition_locator.definition_id
        pre_version_guid = block.location.version_guid

        block.grading_policy['GRADER'][0]['min_count'] = 13
        block.save()  # decache model changes
        updated_block = modulestore().update_item(block, '**replace_user**')

        self.assertNotEqual(updated_block.definition_locator.definition_id, pre_def_id)
        self.assertNotEqual(updated_block.location.version_guid, pre_version_guid)
        self.assertEqual(updated_block.grading_policy['GRADER'][0]['min_count'], 13)

    def test_update_manifold(self):
        """
        Test updating metadata, children, and definition in a single call ensuring all the versioning occurs
        """
        locator = BlockUsageLocator(
            CourseLocator('testx', 'GreekHero', 'run', branch=BRANCH_NAME_DRAFT),
            'problem', block_id='problem1'
        )
        original = modulestore().get_item(locator)
        # first add 2 children to the course for the update to manipulate
        locator = BlockUsageLocator(
            CourseLocator('guestx', 'contender', 'run', branch=BRANCH_NAME_DRAFT),
            'course', block_id="head345679"
        )
        category = 'problem'
        new_payload = "<problem>empty</problem>"
        modulestore().create_item(
            locator, category, 'test_update_manifold',
            fields={'display_name': 'problem 1', 'data': new_payload},
        )
        another_payload = "<problem>not empty</problem>"
        modulestore().create_item(
            locator, category, 'test_update_manifold',
            fields={'display_name': 'problem 2', 'data': another_payload},
            definition_locator=original.definition_locator,
        )
        # pylint: disable=W0212
        modulestore()._clear_cache()

        # now begin the test
        block = modulestore().get_item(locator)
        pre_def_id = block.definition_locator.definition_id
        pre_version_guid = block.location.version_guid

        self.assertNotEqual(block.grading_policy['GRADER'][0]['min_count'], 13)
        block.grading_policy['GRADER'][0]['min_count'] = 13
        block.children = block.children[1:] + [block.children[0]]
        block.advertised_start = "Soon"

        block.save()  # decache model changes
        updated_block = modulestore().update_item(block, "**replace_user**")
        self.assertNotEqual(updated_block.definition_locator.definition_id, pre_def_id)
        self.assertNotEqual(updated_block.location.version_guid, pre_version_guid)
        self.assertEqual(updated_block.grading_policy['GRADER'][0]['min_count'], 13)
        self.assertEqual(updated_block.children[0].version_agnostic(), block.children[0].version_agnostic())
        self.assertEqual(updated_block.advertised_start, "Soon")

    def test_delete_item(self):
        course = self.create_course_for_deletion()
        with self.assertRaises(ValueError):
            modulestore().delete_item(course.location, 'deleting_user')
        reusable_location = course.id.version_agnostic().for_branch(BRANCH_NAME_DRAFT)

        # delete a leaf
        problems = modulestore().get_items(reusable_location, category='problem')
        locn_to_del = problems[0].location
        new_course_loc = modulestore().delete_item(locn_to_del, 'deleting_user')
        deleted = locn_to_del.version_agnostic()
        self.assertFalse(modulestore().has_item(deleted))
        with self.assertRaises(VersionConflictError):
            modulestore().has_item(locn_to_del)

        self.assertTrue(modulestore().has_item(locn_to_del.course_agnostic()))
        self.assertNotEqual(new_course_loc.version_guid, course.location.version_guid)

        # delete a subtree
        nodes = modulestore().get_items(reusable_location, category='chapter')
        new_course_loc = modulestore().delete_item(nodes[0].location, 'deleting_user')
        # check subtree

        def check_subtree(node):
            """
            Check contents of subtree recursively
            """
            if node:
                node_loc = node.location
                self.assertFalse(
                    modulestore().has_item(node_loc.version_agnostic())
                )
                self.assertTrue(modulestore().has_item(node_loc.course_agnostic()))
                if node.has_children:
                    for sub in node.get_children():
                        check_subtree(sub)
        check_subtree(nodes[0])

    def create_course_for_deletion(self):
        """
        Create a course we can delete
        """
        course = modulestore().create_course('nihilx', 'deletion', 'run', 'deleting_user')
        root = course.location.version_agnostic().for_branch(BRANCH_NAME_DRAFT)
        for _ in range(4):
            self.create_subtree_for_deletion(root, ['chapter', 'vertical', 'problem'])
        return modulestore().get_item(root)

    def create_subtree_for_deletion(self, parent, category_queue):
        """
        Create a subtree in the tb deleted course
        """
        if not category_queue:
            return
        node = modulestore().create_item(parent.version_agnostic(), category_queue[0], 'deleting_user')
        node_loc = node.location.map_into_course(parent.course_key)
        for _ in range(4):
            self.create_subtree_for_deletion(node_loc, category_queue[1:])


class TestCourseCreation(SplitModuleTest):
    """
    Test create_course
    """
    def test_simple_creation(self):
        """
        The simplest case but probing all expected results from it.
        """
        # Oddly getting differences of 200nsec
        new_course = modulestore().create_course('test_org', 'test_course', 'test_run', 'create_user')
        new_locator = new_course.location
        # check index entry
        index_info = modulestore().get_course_index_info(new_locator)
        self.assertEqual(index_info['org'], 'test_org')
        self.assertEqual(index_info['edited_by'], 'create_user')
        # check structure info
        structure_info = modulestore().get_course_history_info(new_locator)
        self.assertEqual(structure_info['original_version'], index_info['versions'][BRANCH_NAME_DRAFT])
        self.assertIsNone(structure_info['previous_version'])
        self.assertEqual(structure_info['edited_by'], 'create_user')
        # check the returned course object
        self.assertIsInstance(new_course, CourseDescriptor)
        self.assertEqual(new_course.category, 'course')
        self.assertFalse(new_course.show_calculator)
        self.assertTrue(new_course.allow_anonymous)
        self.assertEqual(len(new_course.children), 0)
        self.assertEqual(new_course.edited_by, "create_user")
        self.assertEqual(len(new_course.grading_policy['GRADER']), 4)
        self.assertDictEqual(new_course.grade_cutoffs, {"Pass": 0.5})

    def test_cloned_course(self):
        """
        Test making a course which points to an existing draft and published but not making any changes to either.
        """
        original_locator = CourseLocator(org='testx', course='wonderful', run="run", branch=BRANCH_NAME_DRAFT)
        original_index = modulestore().get_course_index_info(original_locator)
        new_draft = modulestore().create_course(
            'best', 'leech', 'leech_run', 'leech_master',
            versions_dict=original_index['versions'])
        new_draft_locator = new_draft.location
        self.assertRegexpMatches(new_draft_locator.org, 'best')
        # the edited_by and other meta fields on the new course will be the original author not this one
        self.assertEqual(new_draft.edited_by, 'test@edx.org')
        self.assertEqual(new_draft_locator.version_guid, original_index['versions'][BRANCH_NAME_DRAFT])
        # however the edited_by and other meta fields on course_index will be this one
        new_index = modulestore().get_course_index_info(new_draft_locator)
        self.assertEqual(new_index['edited_by'], 'leech_master')

        new_published_locator = new_draft_locator.course_key.for_branch(BRANCH_NAME_PUBLISHED)
        new_published = modulestore().get_course(new_published_locator)
        self.assertEqual(new_published.edited_by, 'test@edx.org')
        self.assertEqual(new_published.location.version_guid, original_index['versions'][BRANCH_NAME_PUBLISHED])

        # changing this course will not change the original course
        # using new_draft.location will insert the chapter under the course root
        new_item = modulestore().create_item(
            new_draft.location, 'chapter', 'leech_master',
            fields={'display_name': 'new chapter'}
        )
        new_draft_locator = new_draft_locator.course_key.version_agnostic()
        new_index = modulestore().get_course_index_info(new_draft_locator)
        self.assertNotEqual(new_index['versions'][BRANCH_NAME_DRAFT], original_index['versions'][BRANCH_NAME_DRAFT])
        new_draft = modulestore().get_course(new_draft_locator)
        self.assertEqual(new_item.edited_by, 'leech_master')
        self.assertNotEqual(new_item.location.version_guid, original_index['versions'][BRANCH_NAME_DRAFT])
        self.assertNotEqual(new_draft.location.version_guid, original_index['versions'][BRANCH_NAME_DRAFT])
        structure_info = modulestore().get_course_history_info(new_draft_locator)
        self.assertEqual(structure_info['edited_by'], 'leech_master')

        original_course = modulestore().get_course(original_locator)
        self.assertEqual(original_course.location.version_guid, original_index['versions'][BRANCH_NAME_DRAFT])

    def test_derived_course(self):
        """
        Create a new course which overrides metadata and course_data
        """
        original_locator = CourseLocator(org='guestx', course='contender', run="run", branch=BRANCH_NAME_DRAFT)
        original = modulestore().get_course(original_locator)
        original_index = modulestore().get_course_index_info(original_locator)
        fields = {}
        for field in original.fields.values():
            value = getattr(original, field.name)
            if not isinstance(value, datetime.datetime):
                json_value = field.to_json(value)
            else:
                json_value = value
            if field.scope == Scope.content and field.name != 'location':
                fields[field.name] = json_value
            elif field.scope == Scope.settings:
                fields[field.name] = json_value
        fields['grading_policy']['GRADE_CUTOFFS'] = {'A': .9, 'B': .8, 'C': .65}
        fields['display_name'] = 'Derivative'
        new_draft = modulestore().create_course(
            'counter', 'leech', 'leech_run', 'leech_master',
            versions_dict={BRANCH_NAME_DRAFT: original_index['versions'][BRANCH_NAME_DRAFT]},
            fields=fields
        )
        new_draft_locator = new_draft.location
        self.assertRegexpMatches(new_draft_locator.org, 'counter')
        # the edited_by and other meta fields on the new course will be the original author not this one
        self.assertEqual(new_draft.edited_by, 'leech_master')
        self.assertNotEqual(new_draft_locator.version_guid, original_index['versions'][BRANCH_NAME_DRAFT])
        # however the edited_by and other meta fields on course_index will be this one
        new_index = modulestore().get_course_index_info(new_draft_locator)
        self.assertEqual(new_index['edited_by'], 'leech_master')
        self.assertEqual(new_draft.display_name, fields['display_name'])
        self.assertDictEqual(
            new_draft.grading_policy['GRADE_CUTOFFS'],
            fields['grading_policy']['GRADE_CUTOFFS']
        )

    def test_update_course_index(self):
        """
        Test the versions pointers. NOTE: you can change the org, course, or other things, but
        it's not clear how you'd find them again or associate them w/ existing student history since
        we use course_key so many places as immutable.
        """
        locator = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT)
        course_info = modulestore().get_course_index_info(locator)

        # an allowed but not necessarily recommended way to revert the draft version
        head_course = modulestore().get_course(locator)
        versions = course_info['versions']
        versions[BRANCH_NAME_DRAFT] = head_course.previous_version
        modulestore().update_course_index(course_info)
        course = modulestore().get_course(locator)
        self.assertEqual(course.location.version_guid, versions[BRANCH_NAME_DRAFT])

        # an allowed but not recommended way to publish a course
        versions[BRANCH_NAME_PUBLISHED] = versions[BRANCH_NAME_DRAFT]
        modulestore().update_course_index(course_info)
        course = modulestore().get_course(locator.for_branch(BRANCH_NAME_PUBLISHED))
        self.assertEqual(course.location.version_guid, versions[BRANCH_NAME_DRAFT])

    def test_create_with_root(self):
        """
        Test create_course with a specified root id and category
        """
        user = random.getrandbits(32)
        new_course = modulestore().create_course(
            'test_org', 'test_transaction', 'test_run', user,
            root_block_id='top', root_category='chapter'
        )
        self.assertEqual(new_course.location.block_id, 'top')
        self.assertEqual(new_course.category, 'chapter')
        # look at db to verify
        db_structure = modulestore().db_connection.get_structure(
            new_course.location.as_object_id(new_course.location.version_guid)
        )
        self.assertIsNotNone(db_structure, "Didn't find course")
        self.assertNotIn('course', db_structure['blocks'])
        self.assertIn('top', db_structure['blocks'])
        self.assertEqual(db_structure['blocks']['top']['category'], 'chapter')

    def test_create_id_dupe(self):
        """
        Test create_course rejects duplicate id
        """
        user = random.getrandbits(32)
        courses = modulestore().get_courses()
        with self.assertRaises(DuplicateCourseError):
            dupe_course_key = courses[0].location.course_key
            modulestore().create_course(dupe_course_key.org, dupe_course_key.course, dupe_course_key.run, user)


class TestInheritance(SplitModuleTest):
    """
    Test the metadata inheritance mechanism.
    """
    def test_inheritance(self):
        """
        The actual test
        """
        # Note, not testing value where defined (course) b/c there's no
        # defined accessor for it on CourseDescriptor.
        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT), 'problem', 'problem3_2'
        )
        node = modulestore().get_item(locator)
        # inherited
        self.assertEqual(node.graceperiod, datetime.timedelta(hours=2))
        locator = BlockUsageLocator(
            CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT), 'problem', 'problem1'
        )
        node = modulestore().get_item(locator)
        # overridden
        self.assertEqual(node.graceperiod, datetime.timedelta(hours=4))


class TestPublish(SplitModuleTest):
    """
    Test the publishing api
    """
    def setUp(self):
        SplitModuleTest.setUp(self)
        self.user = random.getrandbits(32)

    def tearDown(self):
        SplitModuleTest.tearDown(self)

    def test_publish_safe(self):
        """
        Test the standard patterns: publish to new branch, revise and publish
        """
        source_course = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT)
        dest_course = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_PUBLISHED)
        head = source_course.make_usage_key('course', "head12345")
        chapter1 = source_course.make_usage_key('chapter', 'chapter1')
        chapter2 = source_course.make_usage_key('chapter', 'chapter2')
        chapter3 = source_course.make_usage_key('chapter', 'chapter3')
        modulestore().xblock_publish(self.user, source_course, dest_course, [head], [chapter2, chapter3])
        expected = [head.block_id, chapter1.block_id]
        self._check_course(
            source_course, dest_course, expected, [chapter2.block_id, chapter3.block_id, "problem1", "problem3_2"]
        )
        # add a child under chapter1
        new_module = modulestore().create_item(
            chapter1, "sequential", self.user,
            fields={'display_name': 'new sequential'},
        )
        # remove chapter1 from expected b/c its pub'd version != the source anymore since source changed
        expected.remove(chapter1.block_id)
        # check that it's not in published course
        with self.assertRaises(ItemNotFoundError):
            modulestore().get_item(new_module.location.map_into_course(dest_course))
        # publish it
        modulestore().xblock_publish(self.user, source_course, dest_course, [new_module.location], None)
        expected.append(new_module.location.block_id)
        # check that it is in the published course and that its parent is the chapter
        pub_module = modulestore().get_item(new_module.location.map_into_course(dest_course))
        self.assertEqual(
            modulestore().get_parent_location(pub_module.location).block_id, chapter1.block_id
        )
        # ensure intentionally orphaned blocks work (e.g., course_info)
        new_module = modulestore().create_item(
            source_course, "course_info", self.user, block_id="handouts"
        )
        # publish it
        modulestore().xblock_publish(self.user, source_course, dest_course, [new_module.location], None)
        expected.append(new_module.location.block_id)
        # check that it is in the published course (no error means it worked)
        pub_module = modulestore().get_item(new_module.location.map_into_course(dest_course))
        self._check_course(
            source_course, dest_course, expected, [chapter2.block_id, chapter3.block_id, "problem1", "problem3_2"]
        )

    def test_exceptions(self):
        """
        Test the exceptions which preclude successful publication
        """
        source_course = CourseLocator(org='testx', course='GreekHero', run="run", branch=BRANCH_NAME_DRAFT)
        # destination does not exist
        destination_course = CourseLocator(org='fake', course='Unknown', run="run", branch=BRANCH_NAME_PUBLISHED)
        head = source_course.make_usage_key('course', "head12345")
        chapter3 = source_course.make_usage_key('chapter', 'chapter3')
        problem1 = source_course.make_usage_key('problem', 'problem1')
        with self.assertRaises(ItemNotFoundError):
            modulestore().xblock_publish(self.user, source_course, destination_course, [chapter3], None)
        # publishing into a new branch w/o publishing the root
        destination_course = CourseLocator(org='testx', course='GreekHero', run='run', branch=BRANCH_NAME_PUBLISHED)
        with self.assertRaises(ItemNotFoundError):
            modulestore().xblock_publish(self.user, source_course, destination_course, [chapter3], None)
        # publishing a subdag w/o the parent already in course
        modulestore().xblock_publish(self.user, source_course, destination_course, [head], [chapter3])
        with self.assertRaises(ItemNotFoundError):
            modulestore().xblock_publish(self.user, source_course, destination_course, [problem1], [])

    def test_move_delete(self):
        """
        Test publishing moves and deletes.
        """
        source_course = CourseLocator(org='testx', course='GreekHero', run='run', branch=BRANCH_NAME_DRAFT)
        dest_course = CourseLocator(org='testx', course='GreekHero', run='run', branch=BRANCH_NAME_PUBLISHED)
        head = source_course.make_usage_key('course', "head12345")
        chapter2 = source_course.make_usage_key('chapter', 'chapter2')
        problem1 = source_course.make_usage_key('problem', 'problem1')
        modulestore().xblock_publish(self.user, source_course, dest_course, [head], [chapter2])
        expected = ["head12345", "chapter1", "chapter3", "problem1", "problem3_2"]
        self._check_course(source_course, dest_course, expected, ["chapter2"])
        # now move problem1 and delete problem3_2
        chapter1 = modulestore().get_item(source_course.make_usage_key("chapter", "chapter1"))
        chapter3 = modulestore().get_item(source_course.make_usage_key("chapter", "chapter3"))
        chapter1.children.append(problem1)
        chapter3.children.remove(problem1.map_into_course(chapter3.location.course_key))
        modulestore().delete_item(source_course.make_usage_key("problem", "problem3_2"), self.user)
        modulestore().xblock_publish(self.user, source_course, dest_course, [head], [chapter2])
        expected = ["head12345", "chapter1", "chapter3", "problem1"]
        self._check_course(source_course, dest_course, expected, ["chapter2", "problem3_2"])

    def _check_course(self, source_course_loc, dest_course_loc, expected_blocks, unexpected_blocks):
        """
        Check that the course has the expected blocks and does not have the unexpected blocks
        """
        history_info = modulestore().get_course_history_info(dest_course_loc)
        self.assertEqual(history_info['edited_by'], self.user)
        for expected in expected_blocks:
            # since block_type has no impact on identity, we can just provide an empty string
            source = modulestore().get_item(source_course_loc.make_usage_key("", expected))
            pub_copy = modulestore().get_item(dest_course_loc.make_usage_key("", expected))
            # everything except previous_version & children should be the same
            self.assertEqual(source.category, pub_copy.category)
            self.assertEqual(source.update_version, pub_copy.update_version)
            self.assertEqual(
                self.user, pub_copy.edited_by,
                "{} edited_by {} not {}".format(pub_copy.location, pub_copy.edited_by, self.user)
            )
            for field in source.fields.values():
                if field.name == 'children':
                    self._compare_children(field.read_from(source), field.read_from(pub_copy), unexpected_blocks)
                else:
                    self.assertEqual(field.read_from(source), field.read_from(pub_copy))
        for unexp in unexpected_blocks:
            with self.assertRaises(ItemNotFoundError):
                modulestore().get_item(dest_course_loc.make_usage_key("", unexp))

    def _compare_children(self, source_children, dest_children, unexpected):
        """
        Ensure dest_children == source_children minus unexpected
        """
        dest_cursor = 0
        for child in source_children:
            child = child.version_agnostic()
            if child.block_id in unexpected:
                self.assertNotIn(child.block_id, [dest.block_id for dest in dest_children])
            else:
                self.assertEqual(child.block_id, dest_children[dest_cursor].block_id)
                dest_cursor += 1
        self.assertEqual(dest_cursor, len(dest_children))

class TestSchema(SplitModuleTest):
    """
    Test the db schema (and possibly eventually migrations?)
    """
    def test_schema(self):
        """
        Test that the schema is set in each document
        """
        db_connection = modulestore().db_connection
        for collection in [db_connection.course_index, db_connection.structures, db_connection.definitions]:
            self.assertEqual(
                collection.find({'schema_version': {'$exists': False}}).count(),
                0,
                "{0.name} has records without schema_version".format(collection)
            )
            self.assertEqual(
                collection.find({'schema_version': {'$ne': SplitMongoModuleStore.SCHEMA_VERSION}}).count(),
                0,
                "{0.name} has records with wrong schema_version".format(collection)
            )

#===========================================
def modulestore():
    """
    Mock the django dependent global modulestore function to disentangle tests from django
    """
    def load_function(engine_path):
        """
        Load the given engine
        """
        module_path, _, name = engine_path.rpartition('.')
        return getattr(import_module(module_path), name)

    if SplitModuleTest.modulestore is None:
        class_ = load_function(SplitModuleTest.MODULESTORE['ENGINE'])

        options = {}

        options.update(SplitModuleTest.MODULESTORE['OPTIONS'])
        options['render_template'] = render_to_template_mock

        # pylint: disable=W0142
        SplitModuleTest.modulestore = class_(
            SplitModuleTest.MODULESTORE['DOC_STORE_CONFIG'],
            **options
        )

        SplitModuleTest.bootstrapDB()

    return SplitModuleTest.modulestore


# pylint: disable=W0613
def render_to_template_mock(*args):
    pass
