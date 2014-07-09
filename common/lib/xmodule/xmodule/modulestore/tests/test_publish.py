"""
Test the publish code (mostly testing that publishing doesn't result in orphans)
"""
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.modulestore.tests.test_split_w_old_mongo import SplitWMongoCourseBoostrapper
from xmodule.modulestore.tests.factories import check_mongo_calls
from xmodule.modulestore import ModuleStoreEnum


class TestPublish(SplitWMongoCourseBoostrapper):
    """
    Test the publish code (primary causing orphans)
    """
    def _create_course(self):
        """
        Create the course, publish all verticals
        * some detached items
        """
        # There are 12 created items and 7 parent updates
        # create course: finds: 1 to verify uniqueness, 1 to find parents
        # sends: 1 to create course, 1 to create overview
        with check_mongo_calls(self.draft_mongo, 5, 2):
            super(TestPublish, self)._create_course(split=False)  # 2 inserts (course and overview)

        # with bulk will delay all inheritance computations which won't be added into the mongo_calls
        # TODO with self.draft_mongo.bulk_write_operations(self.old_course_key): instead of
        try:
            self.draft_mongo.begin_bulk_write_operation_on_course(self.old_course_key)
            # finds: 1 for parent to add child, 1 for parent to update edit info
            # sends: 1 for insert, 2 for parent (add child, change edit info)
            with check_mongo_calls(self.draft_mongo, 5, 3):
                self._create_item('chapter', 'Chapter1', {}, {'display_name': 'Chapter 1'}, 'course', 'runid', split=False)

            with check_mongo_calls(self.draft_mongo, 5, 3):
                self._create_item('chapter', 'Chapter2', {}, {'display_name': 'Chapter 2'}, 'course', 'runid', split=False)
            # update info propagation is 2 levels. create looks for draft and then published and then creates
            with check_mongo_calls(self.draft_mongo, 16, 8):
                self._create_item('vertical', 'Vert1', {}, {'display_name': 'Vertical 1'}, 'chapter', 'Chapter1', split=False)
                self._create_item('vertical', 'Vert2', {}, {'display_name': 'Vertical 2'}, 'chapter', 'Chapter1', split=False)
            with check_mongo_calls(self.draft_mongo, 36, 36):
                self._create_item('html', 'Html1', "<p>Goodbye</p>", {'display_name': 'Parented Html'}, 'vertical', 'Vert1', split=False)
                self._create_item(
                    'discussion', 'Discussion1',
                    "discussion discussion_category=\"Lecture 1\" discussion_id=\"a08bfd89b2aa40fa81f2c650a9332846\" discussion_target=\"Lecture 1\"/>\n",
                    {
                        "discussion_category": "Lecture 1",
                        "discussion_target": "Lecture 1",
                        "display_name": "Lecture 1 Discussion",
                        "discussion_id": "a08bfd89b2aa40fa81f2c650a9332846"
                    },
                    'vertical', 'Vert1',
                    split=False
                )
                self._create_item('html', 'Html2', "<p>Hellow</p>", {'display_name': 'Hollow Html'}, 'vertical', 'Vert1', split=False)
                self._create_item(
                    'discussion', 'Discussion2',
                    "discussion discussion_category=\"Lecture 2\" discussion_id=\"b08bfd89b2aa40fa81f2c650a9332846\" discussion_target=\"Lecture 2\"/>\n",
                    {
                        "discussion_category": "Lecture 2",
                        "discussion_target": "Lecture 2",
                        "display_name": "Lecture 2 Discussion",
                        "discussion_id": "b08bfd89b2aa40fa81f2c650a9332846"
                    },
                    'vertical', 'Vert2',
                    split=False
                )
            with check_mongo_calls(self.draft_mongo, 2, 2):
                # 2 finds b/c looking for non-existent parents
                self._create_item('static_tab', 'staticuno', "<p>tab</p>", {'display_name': 'Tab uno'}, None, None, split=False)
                self._create_item('course_info', 'updates', "<ol><li><h2>Sep 22</h2><p>test</p></li></ol>", {}, None, None, split=False)
        finally:  # TODO remove when the bulk write op is available
            self.draft_mongo.end_bulk_write_operation_on_course(self.old_course_key)

    def test_publish_draft_delete(self):
        """
        To reproduce a bug (STUD-811) publish a vertical, convert to draft, delete a child, move a child, publish.
        See if deleted and moved children still is connected or exists in db (bug was disconnected but existed)
        """
        vert_location = self.old_course_key.make_usage_key('vertical', block_id='Vert1')
        item = self.draft_mongo.get_item(vert_location, 2)
        # Vert1 has 3 children; so, publishes 4 nodes which may mean 4 inserts & 1 bulk remove
        # 25-June-2014 find calls are 19. Probably due to inheritance recomputation?
        # 02-July-2014 send calls are 7. 5 from above, plus 2 for updating subtree edit info for Chapter1 and course
        #              find calls are 22. 19 from above, plus 3 for finding the parent of Vert1, Chapter1, and course
        with check_mongo_calls(self.draft_mongo, 22, 7):
            self.draft_mongo.publish(item.location, self.userid)

        # verify status
        item = self.draft_mongo.get_item(vert_location, 0)
        self.assertFalse(getattr(item, 'is_draft', False), "Item was published. Draft should not exist")
        # however, children are still draft, but I'm not sure that's by design

        # delete the draft version of the discussion
        location = self.old_course_key.make_usage_key('discussion', block_id='Discussion1')
        self.draft_mongo.delete_item(location, self.userid)

        draft_vert = self.draft_mongo.get_item(vert_location, 0)
        self.assertTrue(getattr(draft_vert, 'is_draft', False), "Deletion didn't convert parent to draft")
        self.assertNotIn(location, draft_vert.children)
        # move the other child
        other_child_loc = self.old_course_key.make_usage_key('html', block_id='Html2')
        draft_vert.children.remove(other_child_loc)
        other_vert = self.draft_mongo.get_item(self.old_course_key.make_usage_key('vertical', block_id='Vert2'), 0)
        other_vert.children.append(other_child_loc)
        self.draft_mongo.update_item(draft_vert, self.userid)
        self.draft_mongo.update_item(other_vert, self.userid)
        # publish
        self.draft_mongo.publish(vert_location, self.userid)
        item = self.draft_mongo.get_item(draft_vert.location, revision=ModuleStoreEnum.RevisionOption.published_only)
        self.assertNotIn(location, item.children)
        self.assertIsNone(self.draft_mongo.get_parent_location(location))
        with self.assertRaises(ItemNotFoundError):
            self.draft_mongo.get_item(location)
        self.assertNotIn(other_child_loc, item.children)
        self.assertTrue(self.draft_mongo.has_item(other_child_loc), "Oops, lost moved item")
