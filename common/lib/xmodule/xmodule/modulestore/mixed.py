"""
MixedModuleStore allows for aggregation between multiple modulestores.

In this way, courses can be served up both - say - XMLModuleStore or MongoModuleStore

"""

import logging
from uuid import uuid4
from contextlib import contextmanager
from opaque_keys import InvalidKeyError

from . import ModuleStoreWriteBase
from xmodule.modulestore import PublishState
from xmodule.modulestore.django import create_modulestore_instance, loc_mapper
from opaque_keys.edx.locator import CourseLocator, BlockUsageLocator
from xmodule.modulestore.exceptions import ItemNotFoundError
from opaque_keys.edx.keys import CourseKey, UsageKey
from xmodule.modulestore.mongo.base import MongoModuleStore
from xmodule.modulestore.split_mongo.split import SplitMongoModuleStore
from opaque_keys.edx.locations import SlashSeparatedCourseKey
import itertools


log = logging.getLogger(__name__)


class MixedModuleStore(ModuleStoreWriteBase):
    """
    ModuleStore knows how to route requests to the right persistence ms
    """
    def __init__(self, mappings, stores, i18n_service=None, **kwargs):
        """
        Initialize a MixedModuleStore. Here we look into our passed in kwargs which should be a
        collection of other modulestore configuration information
        """
        super(MixedModuleStore, self).__init__(**kwargs)

        self.modulestores = []
        self.mappings = {}

        for course_id, store_name in mappings.iteritems():
            try:
                self.mappings[CourseKey.from_string(course_id)] = store_name
            except InvalidKeyError:
                try:
                    self.mappings[SlashSeparatedCourseKey.from_deprecated_string(course_id)] = store_name
                except InvalidKeyError:
                    log.exception("Invalid MixedModuleStore configuration. Unable to parse course_id %r", course_id)
                    continue

        for store_settings in stores:
            key = store_settings['NAME']
            is_xml = 'XMLModuleStore' in store_settings['ENGINE']
            if is_xml:
                # restrict xml to only load courses in mapping
                store_settings['OPTIONS']['course_ids'] = [
                    course_key.to_deprecated_string()
                    for course_key, store_key in self.mappings.iteritems()
                    if store_key == key
                ]
            store = create_modulestore_instance(
                store_settings['ENGINE'],
                store_settings.get('DOC_STORE_CONFIG', {}),
                store_settings.get('OPTIONS', {}),
                i18n_service=i18n_service,
            )
            if key == 'split':
                store.loc_mapper = loc_mapper()
            # replace all named pointers to the store into actual pointers
            for course_key, store_name in self.mappings.iteritems():
                if store_name == key:
                    self.mappings[course_key] = store
            self.modulestores.append(store)

    def _clean_course_id_for_mapping(self, course_id):
        """
        In order for mapping to work, the course_id must be minimal--no version, no branch--
        as we never store one version or one branch in one ms and another in another ms.

        :param course_id: the CourseKey
        """
        if hasattr(course_id, 'version_agnostic'):
            course_id = course_id.version_agnostic()
        if hasattr(course_id, 'branch_agnostic'):
            course_id = course_id.branch_agnostic()
        return course_id

    def _get_modulestore_for_courseid(self, course_id=None):
        """
        For a given course_id, look in the mapping table and see if it has been pinned
        to a particular modulestore

        If course_id is None, returns the first (ordered) store as the default
        """
        if course_id is not None:
            course_id = self._clean_course_id_for_mapping(course_id)
            mapping = self.mappings.get(course_id, None)
            if mapping is not None:
                return mapping
            else:
                for store in self.modulestores:
                    if isinstance(course_id, store.reference_type) and store.has_course(course_id):
                        self.mappings[course_id] = store
                        return store

        # return the first store, as the default
        return self.modulestores[0]

    def _get_modulestore_by_type(self, modulestore_type):
        """
        This method should only really be used by tests and migration scripts when necessary.
        Returns the module store as requested by type.  The type can be a value from ModuleStoreEnum.Type.
        """
        for store in self.modulestores:
            if store.get_modulestore_type() == modulestore_type:
                return store
        return None

    def has_item(self, usage_key, **kwargs):
        """
        Does the course include the xblock who's id is reference?
        """
        store = self._get_modulestore_for_courseid(usage_key.course_key)
        return store.has_item(usage_key, **kwargs)

    def get_item(self, usage_key, depth=0, **kwargs):
        """
        This method is explicitly not implemented as we need a course_id to disambiguate
        We should be able to fix this when the data-model rearchitecting is done
        """
        store = self._get_modulestore_for_courseid(usage_key.course_key)
        return store.get_item(usage_key, depth, **kwargs)

    def get_items(self, course_key, settings=None, content=None, **kwargs):
        """
        Returns:
            list of XModuleDescriptor instances for the matching items within the course with
            the given course_key

        NOTE: don't use this to look for courses
        as the course_key is required. Use get_courses.

        Args:
            course_key (CourseKey): the course identifier
            settings (dict): fields to look for which have settings scope. Follows same syntax
                and rules as kwargs below
            content (dict): fields to look for which have content scope. Follows same syntax and
                rules as kwargs below.
            kwargs (key=value): what to look for within the course.
                Common qualifiers are ``category`` or any field name. if the target field is a list,
                then it searches for the given value in the list not list equivalence.
                Substring matching pass a regex object.
                For some modulestores, ``name`` is another commonly provided key (Location based stores)
                For some modulestores,
                you can search by ``edited_by``, ``edited_on`` providing either a datetime for == (probably
                useless) or a function accepting one arg to do inequality
        """
        if not isinstance(course_key, CourseKey):
            raise Exception("Must pass in a course_key when calling get_items()")

        store = self._get_modulestore_for_courseid(course_key)
        return store.get_items(course_key, settings, content, **kwargs)

    def get_courses(self):
        '''
        Returns a list containing the top level XModuleDescriptors of the courses in this modulestore.
        '''
        courses = {}  # a dictionary of course keys to course objects

        # first populate with the ones in mappings as the mapping override discovery
        for course_id, store in self.mappings.iteritems():
            course = store.get_course(course_id)
            # check if the course is not None - possible if the mappings file is outdated
            # TODO - log an error if the course is None, but move it to an initialization method to keep it less noisy
            if course is not None:
                courses[course_id] = store.get_course(course_id)

        has_locators = any(issubclass(CourseLocator, store.reference_type) for store in self.modulestores)
        for store in self.modulestores:

            # filter out ones which were fetched from earlier stores but locations may not be ==
            for course in store.get_courses():
                course_id = self._clean_course_id_for_mapping(course.id)
                if course_id not in courses:
                    if has_locators and isinstance(course_id, SlashSeparatedCourseKey):

                        # see if a locator version of course is in the result
                        try:
                            course_locator = loc_mapper().translate_location_to_course_locator(course_id)
                            if course_locator in courses:
                                continue
                        except ItemNotFoundError:
                            # if there's no existing mapping, then the course can't have been in split
                            pass

                    # course is indeed unique. save it in result
                    courses[course_id] = course

        return courses.values()

    def get_course(self, course_key, depth=0):
        """
        returns the course module associated with the course_id. If no such course exists,
        it returns None

        :param course_key: must be a CourseKey
        """
        assert(isinstance(course_key, CourseKey))
        store = self._get_modulestore_for_courseid(course_key)
        try:
            return store.get_course(course_key, depth=depth)
        except ItemNotFoundError:
            return None

    def has_course(self, course_id, ignore_case=False):
        """
        returns the course_id of the course if it was found, else None
        Note: we return the course_id instead of a boolean here since the found course may have
           a different id than the given course_id when ignore_case is True.

        Args:
        * course_id (CourseKey)
        * ignore_case (bool): If True, do a case insensitive search. If
            False, do a case sensitive search
        """
        assert(isinstance(course_id, CourseKey))
        store = self._get_modulestore_for_courseid(course_id)
        return store.has_course(course_id, ignore_case)

    def delete_course(self, course_key, user_id=None):
        """
        See xmodule.modulestore.__init__.ModuleStoreWrite.delete_course
        """
        assert(isinstance(course_key, CourseKey))
        store = self._get_modulestore_for_courseid(course_key)
        if hasattr(store, 'delete_course'):
            return store.delete_course(course_key, user_id)
        else:
            raise NotImplementedError(u"Cannot delete a course on store {}".format(store))

    def get_parent_location(self, location, **kwargs):
        """
        returns the parent locations for a given location
        """
        store = self._get_modulestore_for_courseid(location.course_key)
        return store.get_parent_location(location, **kwargs)

    def get_modulestore_type(self, course_id):
        """
        Returns a type which identifies which modulestore is servicing the given course_id.
        The return can be one of:
        "xml" (for XML based courses),
        "mongo" for old-style MongoDB backed courses,
        "split" for new-style split MongoDB backed courses.
        """
        return self._get_modulestore_for_courseid(course_id).get_modulestore_type()

    def get_orphans(self, course_key):
        """
        Get all of the xblocks in the given course which have no parents and are not of types which are
        usually orphaned. NOTE: may include xblocks which still have references via xblocks which don't
        use children to point to their dependents.
        """
        store = self._get_modulestore_for_courseid(course_key)
        return store.get_orphans(course_key)

    def get_errored_courses(self):
        """
        Return a dictionary of course_dir -> [(msg, exception_str)], for each
        course_dir where course loading failed.
        """
        errs = {}
        for store in self.modulestores:
            errs.update(store.get_errored_courses())
        return errs

    def create_course(self, org, offering, user_id=None, fields=None, **kwargs):
        """
        Creates and returns the course.

        Args:
            org (str): the organization that owns the course
            offering (str): the name of the course offering
            user_id: id of the user creating the course
            fields (dict): Fields to set on the course at initialization
            kwargs: Any optional arguments understood by a subset of modulestores to customize instantiation

        Returns: a CourseDescriptor
        """
        store = self._get_modulestore_for_courseid(None)

        if not hasattr(store, 'create_course'):
            raise NotImplementedError(u"Cannot create a course on store {}".format(store))

        return store.create_course(org, offering, user_id, fields, **kwargs)

    def create_item(self, course_or_parent_loc, category, user_id=None, **kwargs):
        """
        Create and return the item. If parent_loc is a specific location v a course id,
        it installs the new item as a child of the parent (if the parent_loc is a specific
        xblock reference).

        :param course_or_parent_loc: Can be a CourseKey or UsageKey
        :param category (str): The block_type of the item we are creating
        """
        # find the store for the course
        course_id = getattr(course_or_parent_loc, 'course_key', course_or_parent_loc)
        store = self._get_modulestore_for_courseid(course_id)

        location = kwargs.pop('location', None)
        # invoke its create_item
        if isinstance(store, MongoModuleStore):
            block_id = kwargs.pop('block_id', getattr(location, 'name', uuid4().hex))
            parent_loc = course_or_parent_loc if isinstance(course_or_parent_loc, UsageKey) else None
            # must have a legitimate location, compute if appropriate
            if location is None:
                location = course_id.make_usage_key(category, block_id)
            # do the actual creation
            xblock = self.create_and_save_xmodule(location, user_id, **kwargs)
            # don't forget to attach to parent
            if parent_loc is not None and not 'detached' in xblock._class_tags:
                parent = store.get_item(parent_loc)
                parent.children.append(location)
                store.update_item(parent)
        elif isinstance(store, SplitMongoModuleStore):
            if not isinstance(course_or_parent_loc, (CourseLocator, BlockUsageLocator)):
                raise ValueError(u"Cannot create a child of {} in split. Wrong repr.".format(course_or_parent_loc))

            # split handles all the fields in one dict not separated by scope
            fields = kwargs.get('fields', {})
            fields.update(kwargs.pop('metadata', {}))
            fields.update(kwargs.pop('definition_data', {}))
            kwargs['fields'] = fields

            xblock = store.create_item(course_or_parent_loc, category, user_id, **kwargs)
        else:
            raise NotImplementedError(u"Cannot create an item on store %s" % store)

        return xblock

    def update_item(self, xblock, user_id, allow_not_found=False):
        """
        Update the xblock persisted to be the same as the given for all types of fields
        (content, children, and metadata) attribute the change to the given user.
        """
        store = self._verify_modulestore_support(xblock.location, 'update_item')
        return store.update_item(xblock, user_id, allow_not_found)

    def delete_item(self, location, user_id=None, **kwargs):
        """
        Delete the given item from persistence. kwargs allow modulestore specific parameters.
        """
        store = self._verify_modulestore_support(location, 'delete_item')
        store.delete_item(location, user_id=user_id, **kwargs)

    def revert_to_published(self, location, user_id=None):
        """
        Reverts an item to its last published version (recursively traversing all of its descendants).
        If no published version exists, a VersionConflictError is thrown.

        If a published version exists but there is no draft version of this item or any of its descendants, this
        method is a no-op.

        :raises InvalidVersionError: if no published version exists for the location specified
        """
        store = self._verify_modulestore_support(location, 'revert_to_published')
        return store.revert_to_published(location, user_id=user_id)

    def close_all_connections(self):
        """
        Close all db connections
        """
        for mstore in self.modulestores:
            if hasattr(mstore, 'database'):
                mstore.database.connection.close()
            elif hasattr(mstore, 'db'):
                mstore.db.connection.close()

    def create_xmodule(self, location, definition_data=None, metadata=None, runtime=None, fields={}):
        """
        Create the new xmodule but don't save it. Returns the new module.

        :param location: a Location--must have a category
        :param definition_data: can be empty. The initial definition_data for the kvs
        :param metadata: can be empty, the initial metadata for the kvs
        :param runtime: if you already have an xblock from the course, the xblock.runtime value
        :param fields: a dictionary of field names and values for the new xmodule
        """
        store = self._verify_modulestore_support(location, 'create_xmodule')
        return store.create_xmodule(location, definition_data, metadata, runtime, fields)

    def get_courses_for_wiki(self, wiki_slug):
        """
        Return the list of courses which use this wiki_slug
        :param wiki_slug: the course wiki root slug
        :return: list of course locations
        """
        courses = []
        for modulestore in self.modulestores:
            courses.extend(modulestore.get_courses_for_wiki(wiki_slug))
        return courses

    def heartbeat(self):
        """
        Delegate to each modulestore and package the results for the caller.
        """
        # could be done in parallel threads if needed
        return dict(
            itertools.chain.from_iterable(
                store.heartbeat().iteritems()
                for store in self.modulestores
            )
        )

    def compute_publish_state(self, xblock):
        """
        Returns whether this xblock is draft, public, or private.

        Returns:
            PublishState.draft - content is in the process of being edited, but still has a previous
                version deployed to LMS
            PublishState.public - content is locked and deployed to LMS
            PublishState.private - content is editable and not deployed to LMS
        """
        course_id = xblock.scope_ids.usage_id.course_key
        store = self._get_modulestore_for_courseid(course_id)
        if hasattr(store, 'compute_publish_state'):
            return store.compute_publish_state(xblock)
        elif hasattr(store, 'publish'):
            raise NotImplementedError(u"Cannot compute_publish_state on store {}".format(store))
        else:
            # read-only store; so, everything's public
            return PublishState.public

    def publish(self, location, user_id):
        """
        Save a current draft to the underlying modulestore
        Returns the newly published item.
        """
        store = self._verify_modulestore_support(location, 'publish')
        return store.publish(location, user_id)

    def unpublish(self, location, user_id):
        """
        Save a current draft to the underlying modulestore
        Returns the newly unpublished item.
        """
        store = self._verify_modulestore_support(location, 'unpublish')
        return store.unpublish(location, user_id)

    def convert_to_draft(self, location, user_id):
        """
        Create a copy of the source and mark its revision as draft.
        Note: This method is to support the Mongo Modulestore and may be deprecated.

        :param location: the location of the source (its revision must be None)
        """
        store = self._verify_modulestore_support(location, 'convert_to_draft')
        return store.convert_to_draft(location, user_id)

    def has_changes(self, location):
        """
        Checks if the given block has unpublished changes
        :param location: the block to check
        :return: True if the draft and published versions differ
        """
        store = self._verify_modulestore_support(location, 'has_changes')
        return store.has_changes(location)

    def _verify_modulestore_support(self, location, method):
        """
        Finds and returns the store that contains the course for the given location, and verifying
        that the store supports the given method.

        Raises NotImplementedError if the found store does not support the given method.
        """
        course_id = location.course_key
        store = self._get_modulestore_for_courseid(course_id)
        if hasattr(store, method):
            return store
        else:
            raise NotImplementedError(u"Cannot call {} on store {}".format(method, store))


@contextmanager
def store_branch_setting(store, branch_setting):
    """
    A context manager for temporarily setting a store's branch value

    Note: to be effective, the store must be a direct pointer to the underlying store;
        not the intermediary Mixed store.
    """
    assert not isinstance(store, MixedModuleStore)

    try:
        previous_branch_setting_func = store.branch_setting_func
        store.branch_setting_func = lambda: branch_setting
        yield
    finally:
        store.branch_setting_func = previous_branch_setting_func


@contextmanager
def store_bulk_write_operations_on_course(store, course_id):
    """
    A context manager for notifying the store of bulk write events.

    In the case of Mongo, it temporarily disables refreshing the metadata inheritance tree
    until the bulk operation is completed.

    The store can be either the Mixed modulestore or a direct pointer to the underlying store.
    """

    # TODO
    # Make this multi-process-safe if future operations need it.
    # Right now, only Import Course, Clone Course, and Delete Course use this, so
    # it's ok if the cached metadata in the memcache is invalid when another
    # request comes in for the same course.

    # if the caller passed in the mixed modulestore, get a direct pointer to the underlying store
    if hasattr(store, '_get_modulestore_by_course_id'):
        store = store._get_modulestore_by_course_id(course_id)

    try:
        if hasattr(store, 'begin_bulk_write_operation_on_course'):
            store.begin_bulk_write_operation_on_course(course_id)
        yield
    finally:
        if hasattr(store, 'begin_bulk_write_operation_on_course'):
            store.end_bulk_write_operation_on_course(course_id)
