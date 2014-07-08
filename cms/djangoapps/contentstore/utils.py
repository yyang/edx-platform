# pylint: disable=E1103, E1101

import copy
import logging
import re
from datetime import datetime
from pytz import UTC

from django.conf import settings
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from xmodule.contentstore.content import StaticContent
from xmodule.contentstore.django import contentstore
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.mixed import store_bulk_write_operations_on_course
from xmodule.modulestore.exceptions import ItemNotFoundError
from opaque_keys.edx.keys import UsageKey, CourseKey
from xmodule.modulestore.store_utilities import delete_course
from student.roles import CourseInstructorRole, CourseStaffRole


log = logging.getLogger(__name__)

# In order to instantiate an open ended tab automatically, need to have this data
OPEN_ENDED_PANEL = {"name": _("Open Ended Panel"), "type": "open_ended"}
NOTES_PANEL = {"name": _("My Notes"), "type": "notes"}
EXTRA_TAB_PANELS = dict([(p['type'], p) for p in [OPEN_ENDED_PANEL, NOTES_PANEL]])


def delete_course_and_groups(course_id, commit=False):
    """
    This deletes the courseware associated with a course_id as well as cleaning update_item
    the various user table stuff (groups, permissions, etc.)
    """
    module_store = modulestore()
    content_store = contentstore()

    with store_bulk_write_operations_on_course(module_store, course_id):
        if delete_course(module_store, content_store, course_id, commit):

            print 'removing User permissions from course....'
            # in the django layer, we need to remove all the user permissions groups associated with this course
            if commit:
                try:
                    staff_role = CourseStaffRole(course_id)
                    staff_role.remove_users(*staff_role.users_with_role())
                    instructor_role = CourseInstructorRole(course_id)
                    instructor_role.remove_users(*instructor_role.users_with_role())
                except Exception as err:
                    log.error("Error in deleting course groups for {0}: {1}".format(course_id, err))


def get_lms_link_for_item(location, preview=False):
    """
    Returns an LMS link to the course with a jump_to to the provided location.

    :param location: the location to jump to
    :param preview: True if the preview version of LMS should be returned. Default value is false.
    """
    assert(isinstance(location, UsageKey))

    if settings.LMS_BASE is None:
        return None

    if preview:
        lms_base = settings.FEATURES.get('PREVIEW_LMS_BASE')
    else:
        lms_base = settings.LMS_BASE

    return u"//{lms_base}/courses/{course_id}/jump_to/{location}".format(
        lms_base=lms_base,
        course_id=location.course_key.to_deprecated_string(),
        location=location.to_deprecated_string(),
    )


def get_lms_link_for_about_page(course_id):
    """
    Returns the url to the course about page from the location tuple.
    """

    assert(isinstance(course_id, CourseKey))

    if settings.FEATURES.get('ENABLE_MKTG_SITE', False):
        if not hasattr(settings, 'MKTG_URLS'):
            log.exception("ENABLE_MKTG_SITE is True, but MKTG_URLS is not defined.")
            return None

        marketing_urls = settings.MKTG_URLS

        # Root will be "https://www.edx.org". The complete URL will still not be exactly correct,
        # but redirects exist from www.edx.org to get to the Drupal course about page URL.
        about_base = marketing_urls.get('ROOT', None)

        if about_base is None:
            log.exception('There is no ROOT defined in MKTG_URLS')
            return None

        # Strip off https:// (or http://) to be consistent with the formatting of LMS_BASE.
        about_base = re.sub(r"^https?://", "", about_base)

    elif settings.LMS_BASE is not None:
        about_base = settings.LMS_BASE
    else:
        return None

    return u"//{about_base_url}/courses/{course_id}/about".format(
        about_base_url=about_base,
        course_id=course_id.to_deprecated_string()
    )


def course_image_url(course):
    """Returns the image url for the course."""
    loc = StaticContent.compute_location(course.location.course_key, course.course_image)
    path = loc.to_deprecated_string()
    return path


def compute_publish_state(xblock):
    """
    Returns whether this xblock is draft, public, or private.

    Returns:
        PublishState.draft - content is in the process of being edited, but still has a previous
            version deployed to LMS
        PublishState.public - content is locked and deployed to LMS
        PublishState.private - content is editable and not deployed to LMS
    """

    return modulestore().compute_publish_state(xblock)


def is_xblock_visible_to_students(xblock):
    """
    Returns true if there is a published version of the xblock that has been released.
    """

    try:
        published = modulestore().get_item(xblock.location, revision=ModuleStoreEnum.RevisionOption.published_only)
    # If there's no published version then the xblock is clearly not visible
    except ItemNotFoundError:
        return False

    # Check start date
    if 'detached' not in published._class_tags and published.start is not None:
        return datetime.now(UTC) > published.start

    # No start date, so it's always visible
    return True


def add_extra_panel_tab(tab_type, course):
    """
    Used to add the panel tab to a course if it does not exist.
    @param tab_type: A string representing the tab type.
    @param course: A course object from the modulestore.
    @return: Boolean indicating whether or not a tab was added and a list of tabs for the course.
    """
    # Copy course tabs
    course_tabs = copy.copy(course.tabs)
    changed = False
    # Check to see if open ended panel is defined in the course

    tab_panel = EXTRA_TAB_PANELS.get(tab_type)
    if tab_panel not in course_tabs:
        # Add panel to the tabs if it is not defined
        course_tabs.append(tab_panel)
        changed = True
    return changed, course_tabs


def remove_extra_panel_tab(tab_type, course):
    """
    Used to remove the panel tab from a course if it exists.
    @param tab_type: A string representing the tab type.
    @param course: A course object from the modulestore.
    @return: Boolean indicating whether or not a tab was added and a list of tabs for the course.
    """
    # Copy course tabs
    course_tabs = copy.copy(course.tabs)
    changed = False
    # Check to see if open ended panel is defined in the course

    tab_panel = EXTRA_TAB_PANELS.get(tab_type)
    if tab_panel in course_tabs:
        # Add panel to the tabs if it is not defined
        course_tabs = [ct for ct in course_tabs if ct != tab_panel]
        changed = True
    return changed, course_tabs


def reverse_url(handler_name, key_name=None, key_value=None, kwargs=None):
    """
    Creates the URL for the given handler.
    The optional key_name and key_value are passed in as kwargs to the handler.
    """
    kwargs_for_reverse = {key_name: unicode(key_value)} if key_name else None
    if kwargs:
        kwargs_for_reverse.update(kwargs)
    return reverse('contentstore.views.' + handler_name, kwargs=kwargs_for_reverse)


def reverse_course_url(handler_name, course_key, kwargs=None):
    """
    Creates the URL for handlers that use course_keys as URL parameters.
    """
    return reverse_url(handler_name, 'course_key_string', course_key, kwargs)


def reverse_usage_url(handler_name, usage_key, kwargs=None):
    """
    Creates the URL for handlers that use usage_keys as URL parameters.
    """
    return reverse_url(handler_name, 'usage_key_string', usage_key, kwargs)
