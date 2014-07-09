"""
A ModuleStore that knows about a special version DRAFT. Modules
marked as DRAFT are read in preference to modules without the DRAFT
version by this ModuleStore (so, access to i4x://org/course/cat/name
returns the i4x://org/course/cat/name@draft object if that exists,
and otherwise returns i4x://org/course/cat/name).
"""

import pymongo

from xmodule.exceptions import InvalidVersionError
from xmodule.modulestore import PublishState, ModuleStoreEnum
from xmodule.modulestore.exceptions import ItemNotFoundError, DuplicateItemError, InvalidBranchSetting
from xmodule.modulestore.mongo.base import (
    MongoModuleStore, MongoRevisionKey, as_draft, as_published,
    DIRECT_ONLY_CATEGORIES, SORT_REVISION_FAVOR_DRAFT
)
from opaque_keys.edx.locations import Location


def wrap_draft(item):
    """
    Cleans the item's location and sets the `is_draft` attribute if needed.

    Sets `item.is_draft` to `True` if the item is DRAFT, and `False` otherwise.
    Sets the item's location to the non-draft location in either case.
    """
    setattr(item, 'is_draft', item.location.revision == MongoRevisionKey.draft)
    item.location = item.location.replace(revision=MongoRevisionKey.published)
    return item


class DraftModuleStore(MongoModuleStore):
    """
    This mixin modifies a modulestore to give it draft semantics.
    Edits made to units are stored to locations that have the revision DRAFT.
    Reads are first read with revision DRAFT, and then fall back
    to the baseline revision only if DRAFT doesn't exist.

    This module also includes functionality to promote DRAFT modules (and their children)
    to published modules.
    """

    def __init__(self, *args, **kwargs):
        """
        Args:
            branch_setting_func: a function that returns the branch setting to use for this store's operations
        """
        super(DraftModuleStore, self).__init__(*args, **kwargs)
        self.branch_setting_func = kwargs.pop('branch_setting_func', lambda: ModuleStoreEnum.Branch.published_only)

    def get_item(self, usage_key, depth=0, revision=None):
        """
        Returns an XModuleDescriptor instance for the item at usage_key.

        Args:
            usage_key: A :class:`.UsageKey` instance

            depth (int): An argument that some module stores may use to prefetch
                descendants of the queried modules for more efficient results later
                in the request. The depth is counted in the number of calls to
                get_children() to cache.  None indicates to cache all descendants.

            revision:
                ModuleStoreEnum.RevisionOption.published_only - returns only the published item.
                ModuleStoreEnum.RevisionOption.draft_only - returns only the draft item.
                None - uses the branch setting as follows:
                    if branch setting is ModuleStoreEnum.Branch.published_only, returns only the published item.
                    if branch setting is ModuleStoreEnum.Branch.draft_preferred, returns either draft or published item,
                        preferring draft.

                Note: If the item is in DIRECT_ONLY_CATEGORIES, then returns only the PUBLISHED
                version regardless of the revision.

        Raises:
            xmodule.modulestore.exceptions.InsufficientSpecificationError
            if any segment of the usage_key is None except revision

            xmodule.modulestore.exceptions.ItemNotFoundError if no object
            is found at that usage_key
        """
        def get_published():
            return wrap_draft(super(DraftModuleStore, self).get_item(usage_key, depth=depth))

        def get_draft():
            return wrap_draft(super(DraftModuleStore, self).get_item(as_draft(usage_key), depth=depth))

        # return the published version if ModuleStoreEnum.RevisionOption.published_only is requested
        if revision == ModuleStoreEnum.RevisionOption.published_only:
            return get_published()

        # if the item is direct-only, there can only be a published version
        elif usage_key.category in DIRECT_ONLY_CATEGORIES:
            return get_published()

        # return the draft version (without any fallback to PUBLISHED) if DRAFT-ONLY is requested
        elif revision == ModuleStoreEnum.RevisionOption.draft_only:
            return get_draft()

        elif self.branch_setting_func() == ModuleStoreEnum.Branch.published_only:
            return get_published()

        else:
            # could use a single query wildcarding revision and sorting by revision. would need to
            # use prefix form of to_deprecated_son
            try:
                # first check for a draft version
                return get_draft()
            except ItemNotFoundError:
                # otherwise, fall back to the published version
                return get_published()

    def has_item(self, usage_key, revision=None):
        """
        Returns True if location exists in this ModuleStore.

        Args:
            revision:
                ModuleStoreEnum.RevisionOption.published_only - checks for the published item only
                ModuleStoreEnum.RevisionOption.draft_only - checks for the draft item only
                None - uses the branch setting, as follows:
                    if branch setting is ModuleStoreEnum.Branch.published_only, checks for the published item only
                    if branch setting is ModuleStoreEnum.Branch.draft_preferred, checks whether draft or published item exists
        """
        def has_published():
            return super(DraftModuleStore, self).has_item(usage_key)

        def has_draft():
            return super(DraftModuleStore, self).has_item(as_draft(usage_key))

        if revision == ModuleStoreEnum.RevisionOption.draft_only:
            return has_draft()
        elif revision == ModuleStoreEnum.RevisionOption.published_only \
                or self.branch_setting_func() == ModuleStoreEnum.Branch.published_only:
            return has_published()
        else:
            key = usage_key.to_deprecated_son(prefix='_id.')
            del key['_id.revision']
            return self.collection.find(key).count() > 0

    def _get_raw_parent_locations(self, location, key_revision):
        """
        Get the parents but don't unset the revision in their locations.

        Intended for internal use but not restricted.

        Args:
            location (UsageKey): assumes the location's revision is None; so, uses revision keyword solely
            key_revision:
                MongoRevisionKey.draft - return only the draft parent
                MongoRevisionKey.published - return only the published parent
                ModuleStoreEnum.RevisionOption.all - return both draft and published parents
        """
        _verify_revision_is_published(location)

        # create a query to find all items in the course that have the given location listed as a child
        query = self._course_key_to_son(location.course_key)
        query['definition.children'] = location.to_deprecated_string()

        # find all the items that satisfy the query
        parents = self.collection.find(query, {'_id': True}, sort=[SORT_REVISION_FAVOR_DRAFT])

        # return only the parent(s) that satisfy the request
        return [
            Location._from_deprecated_son(parent['_id'], location.course_key.run)
            for parent in parents
            if (
                # return all versions of the parent if revision is ModuleStoreEnum.RevisionOption.all
                key_revision == ModuleStoreEnum.RevisionOption.all or
                # return this parent if it's direct-only, regardless of which revision is requested
                parent['_id']['category'] in DIRECT_ONLY_CATEGORIES or
                # return this parent only if its revision matches the requested one
                parent['_id']['revision'] == key_revision
            )
        ]

    def get_parent_location(self, location, revision=None, **kwargs):
        '''
        Returns the given location's parent location in this course.

        Returns: version agnostic locations (revision always None) as per the rest of mongo.

        Args:
            revision:
                None - uses the branch setting for the revision
                ModuleStoreEnum.RevisionOption.published_only
                    - return only the PUBLISHED parent if it exists, else returns None
                ModuleStoreEnum.RevisionOption.draft_preferred
                    - return either the DRAFT or PUBLISHED parent, preferring DRAFT, if parent(s) exists,
                        else returns None

                    If the draft has a different parent than the published, it returns only
                    the draft's parent. Because parents don't record their children's revisions, this
                    is actually a potentially fragile deduction based on parent type. If the parent type
                    is not DIRECT_ONLY, then the parent revision must be DRAFT.
                    Only xml_exporter currently uses this argument. Others should avoid it.
        '''
        if revision is None:
            revision = ModuleStoreEnum.RevisionOption.published_only \
                if self.branch_setting_func() == ModuleStoreEnum.Branch.published_only \
                else ModuleStoreEnum.RevisionOption.draft_preferred
        return super(DraftModuleStore, self).get_parent_location(location, revision, **kwargs)

    def create_xmodule(self, location, definition_data=None, metadata=None, runtime=None, fields={}):
        """
        Create the new xmodule but don't save it. Returns the new module with a draft locator if
        the category allows drafts. If the category does not allow drafts, just creates a published module.

        :param location: a Location--must have a category
        :param definition_data: can be empty. The initial definition_data for the kvs
        :param metadata: can be empty, the initial metadata for the kvs
        :param runtime: if you already have an xmodule from the course, the xmodule.runtime value
        :param fields: a dictionary of field names and values for the new xmodule
        """
        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)

        if location.category not in DIRECT_ONLY_CATEGORIES:
            location = as_draft(location)
        return wrap_draft(
            super(DraftModuleStore, self).create_xmodule(location, definition_data, metadata, runtime, fields)
        )

    def get_items(self, course_key, settings=None, content=None, revision=None, **kwargs):
        """
        Performance Note: This is generally a costly operation, but useful for wildcard searches.

        Returns:
            list of XModuleDescriptor instances for the matching items within the course with
            the given course_key

        NOTE: don't use this to look for courses as the course_key is required. Use get_courses instead.

        Args:
            course_key (CourseKey): the course identifier
            settings: not used
            content: not used
            revision:
                ModuleStoreEnum.RevisionOption.published_only - returns only Published items
                ModuleStoreEnum.RevisionOption.draft_only - returns only Draft items
                None - uses the branch setting, as follows:
                    if the branch setting is ModuleStoreEnum.Branch.published_only,
                        returns only Published items
                    if the branch setting is ModuleStoreEnum.Branch.draft_preferred,
                        returns either Draft or Published, preferring Draft items.
            kwargs (key=value): what to look for within the course.
                Common qualifiers are ``category`` or any field name. if the target field is a list,
                then it searches for the given value in the list not list equivalence.
                Substring matching pass a regex object.
                ``name`` is another commonly provided key (Location based stores)
        """
        def base_get_items(key_revision):
            return super(DraftModuleStore, self).get_items(course_key, key_revision=key_revision, **kwargs)

        def draft_items():
            return [wrap_draft(item) for item in base_get_items(MongoRevisionKey.draft)]

        def published_items(draft_items):
            # filters out items that are not already in draft_items
            draft_items_locations = {item.location for item in draft_items}
            return [
                item for item in
                base_get_items(MongoRevisionKey.published)
                if item.location not in draft_items_locations
            ]

        if revision == ModuleStoreEnum.RevisionOption.draft_only:
            return draft_items()
        elif revision == ModuleStoreEnum.RevisionOption.published_only \
                or self.branch_setting_func() == ModuleStoreEnum.Branch.published_only:
            return published_items([])
        else:
            draft_items = draft_items()
            return draft_items + published_items(draft_items)

    def convert_to_draft(self, location, user_id):
        """
        Copy the subtree rooted at source_location and mark the copies as draft.

        Args:
            location: the location of the source (its revision must be None)
            user_id: the ID of the user doing the operation

        Raises:
            InvalidVersionError: if the source can not be made into a draft
            ItemNotFoundError: if the source does not exist
            DuplicateItemError: if the source or any of its descendants already has a draft copy
        """
        # delegating to internal b/c we don't want any public user to use the kwargs on the internal
        return self._convert_to_draft(location, user_id)

    def _convert_to_draft(self, location, user_id, delete_published=False, ignore_if_draft=False):
        """
        Internal method with additional internal parameters to convert a subtree to draft.

        Args:
            location: the location of the source (its revision must be MongoRevisionKey.published)
            user_id: the ID of the user doing the operation
            delete_published (Boolean): intended for use by unpublish
            ignore_if_draft(Boolean): for internal use only as part of depth first change

        Raises:
            InvalidVersionError: if the source can not be made into a draft
            ItemNotFoundError: if the source does not exist
            DuplicateItemError: if the source or any of its descendants already has a draft copy
        """
        # verify input conditions
        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)
        _verify_revision_is_published(location)

        # ensure we are not creating a DRAFT of an item that is direct-only
        if location.category in DIRECT_ONLY_CATEGORIES:
            raise InvalidVersionError(location)

        def convert_item(item, to_be_deleted):
            """
            Convert the subtree
            """
            # collect the children's ids for future processing
            next_tier = []
            for child in item.get('definition', {}).get('children', []):
                child_loc = Location.from_deprecated_string(child)
                next_tier.append(child_loc.to_deprecated_son())

            # insert a new DRAFT version of the item
            item['_id']['revision'] = MongoRevisionKey.draft
            # ensure keys are in fixed and right order before inserting
            item['_id'] = self._id_dict_to_son(item['_id'])
            try:
                self.collection.insert(item)
            except pymongo.errors.DuplicateKeyError:
                # prevent re-creation of DRAFT versions, unless explicitly requested to ignore
                if not ignore_if_draft:
                    raise DuplicateItemError(item['_id'], self, 'collection')

            # delete the old PUBLISHED version if requested
            if delete_published:
                item['_id']['revision'] = MongoRevisionKey.published
                to_be_deleted.append(item['_id'])

            return next_tier

        # convert the subtree using the original item as the root
        self._breadth_first(convert_item, [location])

        # return the new draft item (does another fetch)
        # get_item will wrap_draft so don't call it here (otherwise, it would override the is_draft attribute)
        return self.get_item(location)

    def update_item(self, xblock, user_id=None, allow_not_found=False, force=False, isPublish=False):
        """
        See superclass doc.
        In addition to the superclass's behavior, this method converts the unit to draft if it's not
        direct-only and not already draft.
        """
        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)

        # if the xblock is direct-only, update the PUBLISHED version
        if xblock.location.category in DIRECT_ONLY_CATEGORIES:
            return super(DraftModuleStore, self).update_item(xblock, user_id, allow_not_found)

        draft_loc = as_draft(xblock.location)
        if not super(DraftModuleStore, self).has_item(draft_loc):
            try:
                # ignore any descendants which are already draft
                self._convert_to_draft(xblock.location, user_id, ignore_if_draft=True)
            except ItemNotFoundError as exception:
                # ignore the exception only if allow_not_found is True and
                # the item that wasn't found is the one that was passed in
                # we make this extra location check so we do not hide errors when converting any children to draft
                if not (allow_not_found and exception.args[0] == xblock.location):
                    raise

        xblock.location = draft_loc
        super(DraftModuleStore, self).update_item(xblock, user_id, allow_not_found, isPublish=isPublish)
        return wrap_draft(xblock)

    def delete_item(self, location, user_id, revision=None, **kwargs):
        """
        Delete an item from this modulestore.
        The method determines which revisions to delete. It disconnects and deletes the subtree.
        In general, it assumes deletes only occur on drafts except for direct_only. The only exceptions
        are internal calls like deleting orphans (during publishing as well as from delete_orphan view).
        To indicate that all versions should be deleted, pass the keyword revision=ModuleStoreEnum.RevisionOption.all.

        * Deleting a DIRECT_ONLY_CATEGORIES block, deletes both draft and published children and removes from parent.
        * Deleting a specific version of block whose parent is of DIRECT_ONLY_CATEGORIES, only removes it from parent if
        the other version of the block does not exist. Deletes only children of same version.
        * Other deletions remove from parent of same version and subtree of same version

        Args:
            location: UsageKey of the item to be deleted
            user_id: id of the user deleting the item
            revision:
                None - deletes the item and its subtree, and updates the parents per description above
                ModuleStoreEnum.RevisionOption.published_only - removes only Published versions
                ModuleStoreEnum.RevisionOption.all - removes both Draft and Published parents
                    currently only provided by contentstore.views.item.orphan_handler
        """
        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)
        _verify_revision_is_published(location)

        is_item_direct_only = location.category in DIRECT_ONLY_CATEGORIES
        if is_item_direct_only or revision == ModuleStoreEnum.RevisionOption.published_only:
            parent_revision = MongoRevisionKey.published
        elif revision == ModuleStoreEnum.RevisionOption.all:
            parent_revision = ModuleStoreEnum.RevisionOption.all
        else:
            parent_revision = MongoRevisionKey.draft

        # remove subtree from its parent
        parent_locations = self._get_raw_parent_locations(location, key_revision=parent_revision)
        # if no parents, then we're trying to delete something which we should convert to draft
        if not parent_locations:
            # find the published parent, convert it to draft, then manipulate the draft
            parent_locations = self._get_raw_parent_locations(location, key_revision=MongoRevisionKey.published)
            # parent_locations will still be empty if the object was an orphan
            if parent_locations:
                draft_parent = self.convert_to_draft(parent_locations[0], user_id)
                parent_locations = [draft_parent.location]
        # there could be 2 parents if
        #   Case 1: the draft item moved from one parent to another
        #   Case 2: revision==ModuleStoreEnum.RevisionOption.all and the single parent has 2 versions: draft and published
        for parent_location in parent_locations:
            # don't remove from direct_only parent if other versions of this still exists
            if not is_item_direct_only and parent_location.category in DIRECT_ONLY_CATEGORIES:
                # see if other version of root exists
                alt_location = location.replace(
                    revision=MongoRevisionKey.published
                    if location.revision == MongoRevisionKey.draft
                    else MongoRevisionKey.draft
                )
                if super(DraftModuleStore, self).has_item(alt_location):
                    continue

            parent_block = super(DraftModuleStore, self).get_item(parent_location)
            parent_block.children.remove(location)
            parent_block.location = parent_location  # ensure the location is with the correct revision
            self.update_item(parent_block, user_id)

        if is_item_direct_only or revision == ModuleStoreEnum.RevisionOption.all:
            as_functions = [as_draft, as_published]
        elif revision == ModuleStoreEnum.RevisionOption.published_only:
            as_functions = [as_published]
        else:
            as_functions = [as_draft]
        self._delete_subtree(location, as_functions)

    def _delete_subtree(self, location, as_functions):
        """
        Internal method for deleting all of the subtree whose revisions match the as_functions
        """
        course_key = location.course_key

        def _delete_item(current_entry, to_be_deleted):
            """
            Depth first deletion of nodes
            """
            to_be_deleted.append(self._id_dict_to_son(current_entry['_id']))
            next_tier = []
            for child_loc in current_entry.get('definition', {}).get('children', []):
                child_loc = course_key.make_usage_key_from_deprecated_string(child_loc)
                for rev_func in as_functions:
                    current_loc = rev_func(child_loc)
                    current_son = current_loc.to_deprecated_son()
                    next_tier.append(current_son)

            return next_tier

        first_tier = [as_func(location) for as_func in as_functions]
        self._breadth_first(_delete_item, first_tier)

    def _breadth_first(self, function, root_usages):
        """
        Get the root_usage from the db and do a depth first scan. Call the function on each. The
        function should return a list of SON for any next tier items to process and should
        add the SON for any items to delete to the to_be_deleted array.

        At the end, it mass deletes the to_be_deleted items and refreshes the cached metadata inheritance
        tree.

        :param function: a function taking (item, to_be_deleted) and returning [SON] for next_tier invocation
        :param root_usages: the usage keys for the root items (ensure they have the right revision set)
        """
        if len(root_usages) == 0:
            return
        to_be_deleted = []

        def _internal(tier):
            next_tier = []
            tier_items = self.collection.find({'_id': {'$in': tier}})
            for current_entry in tier_items:
                next_tier.extend(function(current_entry, to_be_deleted))

            if len(next_tier) > 0:
                _internal(next_tier)

        _internal([root_usage.to_deprecated_son() for root_usage in root_usages])
        self.collection.remove({'_id': {'$in': to_be_deleted}}, safe=self.collection.safe)
        # recompute (and update) the metadata inheritance tree which is cached
        self.refresh_cached_metadata_inheritance_tree(root_usages[0].course_key)

    def has_changes(self, location):
        """
        Check if the xblock or its children have been changed since the last publish.
        :param location: location to check
        :return: True if the draft and published versions differ
        """

        item = self.get_item(location)

        # don't check children if this block has changes (is not public)
        if self.compute_publish_state(item) != PublishState.public:
            return True
        # if this block doesn't have changes, then check its children
        elif item.has_children:
            return any([self.has_changes(child) for child in item.children])
        # otherwise there are no changes
        else:
            return False

    def publish(self, location, user_id):
        """
        Publish the subtree rooted at location to the live course and remove the drafts.
        Such publishing may cause the deletion of previously published but subsequently deleted
        child trees. Overwrites any existing published xblocks from the subtree.

        Treats the publishing of non-draftable items as merely a subtree selection from
        which to descend.

        Raises:
            ItemNotFoundError: if any of the draft subtree nodes aren't found
        """
        # NOTE: cannot easily use self._breadth_first b/c need to get pub'd and draft as pairs
        # (could do it by having 2 breadth first scans, the first to just get all published children
        # and the second to do the publishing on the drafts looking for the published in the cached
        # list of published ones.)
        to_be_deleted = []

        def _internal_depth_first(item_location, is_root):
            """
            Depth first publishing from the given location
            """
            item = self.get_item(item_location)

            # publish the children first
            if item.has_children:
                for child_loc in item.children:
                    _internal_depth_first(child_loc, False)

            if item_location.category in DIRECT_ONLY_CATEGORIES or not getattr(item, 'is_draft', False):
                # ignore noop attempt to publish something that can't be or isn't currently draft
                return

            # try to find the originally PUBLISHED version, if it exists
            try:
                original_published = super(DraftModuleStore, self).get_item(item_location)
            except ItemNotFoundError:
                original_published = None

            # if the category of this item allows having children
            if item.has_children:
                if original_published is not None:
                    # see if previously published children were deleted. 2 reasons for children lists to differ:
                    #   Case 1: child deleted
                    #   Case 2: child moved
                    for orig_child in original_published.children:
                        if orig_child not in item.children:
                            published_parent = self.get_parent_location(orig_child)
                            if published_parent == item_location:
                                # Case 1: child was deleted in draft parent item
                                # So, delete published version of the child now that we're publishing the draft parent
                                self._delete_subtree(orig_child, [as_published])
                            else:
                                # Case 2: child was moved to a new draft parent item
                                # So, do not delete the child.  It will be published when the new parent is published.
                                pass

            super(DraftModuleStore, self).update_item(item, user_id, isPublish=True, is_publish_root=is_root)
            to_be_deleted.append(as_draft(item_location).to_deprecated_son())

        # verify input conditions
        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)
        _verify_revision_is_published(location)

        _internal_depth_first(location, True)
        if len(to_be_deleted) > 0:
            self.collection.remove({'_id': {'$in': to_be_deleted}})
        return self.get_item(as_published(location))

    def unpublish(self, location, user_id):
        """
        Turn the published version into a draft, removing the published version.

        NOTE: unlike publish, this gives an error if called above the draftable level as it's intended
        to remove things from the published version
        """
        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)
        return self._convert_to_draft(location, user_id, delete_published=True)

    def revert_to_published(self, location, user_id=None):
        """
        Reverts an item to its last published version (recursively traversing all of its descendants).
        If no published version exists, a VersionConflictError is thrown.

        If a published version exists but there is no draft version of this item or any of its descendants, this
        method is a no-op. It is also a no-op if the root item is in DIRECT_ONLY_CATEGORIES.

        :raises InvalidVersionError: if no published version exists for the location specified
        """
        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)
        _verify_revision_is_published(location)

        if location.category in DIRECT_ONLY_CATEGORIES:
            return

        if not self.has_item(location, revision=ModuleStoreEnum.RevisionOption.published_only):
            raise InvalidVersionError(location)

        def delete_draft_only(root_location):
            """
            Helper function that calls delete on the specified location if a draft version of the item exists.
            If no draft exists, this function recursively calls itself on the children of the item.
            """
            query = root_location.to_deprecated_son(prefix='_id.')
            del query['_id.revision']
            versions_found = self.collection.find(
                query, {'_id': True, 'definition.children': True}, sort=[SORT_REVISION_FAVOR_DRAFT]
            )
            # If 2 versions versions exist, we can assume one is a published version. Go ahead and do the delete
            # of the draft version.
            if versions_found.count() > 1:
                self._delete_subtree(root_location, [as_draft])
            elif versions_found.count() == 1:
                # Since this method cannot be called on something in DIRECT_ONLY_CATEGORIES and we call
                # delete_subtree as soon as we find an item with a draft version, if there is only 1 version
                # it must be published (since adding a child to a published item creates a draft of the parent).
                item = versions_found[0]
                assert item.get('_id').get('revision') != MongoRevisionKey.draft
                for child in item.get('definition', {}).get('children', []):
                    child_loc = Location.from_deprecated_string(child)
                    delete_draft_only(child_loc)

        delete_draft_only(location)

    def _query_children_for_cache_children(self, course_key, items):
        # first get non-draft in a round-trip
        to_process_non_drafts = super(DraftModuleStore, self)._query_children_for_cache_children(course_key, items)

        to_process_dict = {}
        for non_draft in to_process_non_drafts:
            to_process_dict[Location._from_deprecated_son(non_draft["_id"], course_key.run)] = non_draft

        if self.branch_setting_func() == ModuleStoreEnum.Branch.draft_preferred:
            # now query all draft content in another round-trip
            query = []
            for item in items:
                item_usage_key = course_key.make_usage_key_from_deprecated_string(item)
                if item_usage_key.category not in DIRECT_ONLY_CATEGORIES:
                    query.append(as_draft(item_usage_key).to_deprecated_son())
            if query:
                query = {'_id': {'$in': query}}
                to_process_drafts = list(self.collection.find(query))

                # now we have to go through all drafts and replace the non-draft
                # with the draft. This is because the semantics of the DraftStore is to
                # always return the draft - if available
                for draft in to_process_drafts:
                    draft_loc = Location._from_deprecated_son(draft["_id"], course_key.run)
                    draft_as_non_draft_loc = as_published(draft_loc)

                    # does non-draft exist in the collection
                    # if so, replace it
                    if draft_as_non_draft_loc in to_process_dict:
                        to_process_dict[draft_as_non_draft_loc] = draft

        # convert the dict - which is used for look ups - back into a list
        queried_children = to_process_dict.values()

        return queried_children

    def compute_publish_state(self, xblock):
        """
        Returns whether this xblock is draft, public, or private.

        Returns:
            PublishState.draft - content is in the process of being edited, but still has a previous
                version deployed to LMS
            PublishState.public - content is locked and deployed to LMS
            PublishState.private - content is editable and not deployed to LMS
        """
        if getattr(xblock, 'is_draft', False):
            published_xblock_location = as_published(xblock.location)
            published_item = self.collection.find_one(
                {'_id': published_xblock_location.to_deprecated_son()}
            )
            if published_item is None:
                return PublishState.private
            else:
                return PublishState.draft
        else:
            return PublishState.public

    def _verify_branch_setting(self, expected_branch_setting):
        """
        Raises an exception if the current branch setting does not match the expected branch setting.
        """
        actual_branch_setting = self.branch_setting_func()
        if actual_branch_setting != expected_branch_setting:
            raise InvalidBranchSetting(
                expected_setting=expected_branch_setting,
                actual_setting=actual_branch_setting
            )


def _verify_revision_is_published(location):
    """
    Asserts that the revision set on the given location is MongoRevisionKey.published
    """
    assert location.revision == MongoRevisionKey.published
