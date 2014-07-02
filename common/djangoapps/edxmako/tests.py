from django.conf import settings
from django.http import HttpResponse
from django.test import TestCase
from django.test.utils import override_settings
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from edxmako import add_lookup, LOOKUP
from edxmako.shortcuts import marketing_link
import edxmako.middleware
from student.tests.factories import UserFactory
from mock import patch, Mock
import unittest
from util.testing import UrlResetMixin


class ShortcutsTests(UrlResetMixin, TestCase):
    """
    Test the edxmako shortcuts file
    """
    @override_settings(MKTG_URLS={'ROOT': 'dummy-root', 'ABOUT': '/about-us'})
    @override_settings(MKTG_URL_LINK_MAP={'ABOUT': 'login'})
    def test_marketing_link(self):
        # test marketing site on
        with patch.dict('django.conf.settings.FEATURES', {'ENABLE_MKTG_SITE': True}):
            expected_link = 'dummy-root/about-us'
            link = marketing_link('ABOUT')
            self.assertEquals(link, expected_link)
        # test marketing site off
        with patch.dict('django.conf.settings.FEATURES', {'ENABLE_MKTG_SITE': False}):
            # we are using login because it is common across both cms and lms
            expected_link = reverse('login')
            link = marketing_link('ABOUT')
            self.assertEquals(link, expected_link)


class AddLookupTests(TestCase):
    """
    Test the `add_lookup` function.
    """
    @patch('edxmako.LOOKUP', {})
    def test_with_package(self):
        add_lookup('test', 'management', __name__)
        dirs = LOOKUP['test'].directories
        self.assertEqual(len(dirs), 1)
        self.assertTrue(dirs[0].endswith('management'))


class MakoMiddlewareTest(TestCase):
    """
    Test MakoMiddleware.
    """

    def setUp(self):
        self.middleware = edxmako.middleware.MakoMiddleware()
        self.user = UserFactory.create()
        self.course_id = 'mock/course/id'
        self.url = reverse("courseware", kwargs={'course_id': self.course_id})
        self.request = RequestFactory().get(self.url)
        self.request.user = self.user
        self.response = Mock(spec=HttpResponse)

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_clear_request_context_variable(self):
        """
        Test clear requestcontext global variable.
        """

        # Execute process request using the request.
        self.middleware.process_request(self.request)
        # requestcontext should not be None.
        self.assertIsNotNone(edxmako.middleware.requestcontext)

        # Execute process response using the request and response.
        self.middleware.process_response(self.request, self.response)
        # requestcontext should be None.
        self.assertIsNone(edxmako.middleware.requestcontext)
