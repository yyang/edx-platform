define([
    'js/models/course', 'js/models/group_configuration',
    'js/collections/group_configuration',
    'js/views/group_configuration_details',
    'js/views/group_configurations_list', 'js/views/group_configuration_edit',
    'js/views/group_configuration_item', 'js/models/group',
    'js/collections/group', 'js/views/group_edit',
    'js/views/feedback_notification', 'js/spec_helpers/create_sinon',
    'js/spec_helpers/edit_helpers', 'squire', 'jasmine-stealth'
], function(
    Course, GroupConfigurationModel, GroupConfigurationCollection,
    GroupConfigurationDetails, GroupConfigurationsList, GroupConfigurationEdit,
    GroupConfigurationItem, GroupModel, GroupCollection, GroupEdit,
    Notification, create_sinon, view_helpers, Squire
) {
    'use strict';
    var SELECTORS = {
        detailsView: '.view-group-configuration-details',
        editView: '.view-group-configuration-edit',
        itemView: '.group-configurations-list-item',
        group: '.group',
        groupFields: '.groups-fields',
        name: '.group-configuration-name',
        description: '.group-configuration-description',
        groupsCount: '.group-configuration-groups-count',
        groupsAllocation: '.group-allocation',
        errorMessage: '.group-configuration-edit-error',
        inputGroupName: '.group-name',
        inputName: '.group-configuration-name-input',
        inputDescription: '.group-configuration-description-input'
    };

    beforeEach(function() {
        window.course = new Course({
            id: '5',
            name: 'Course Name',
            url_name: 'course_name',
            org: 'course_org',
            num: 'course_num',
            revision: 'course_rev'
        });

        this.addMatchers({
            toContainText: function(text) {
                var trimmedText = $.trim(this.actual.text());

                if (text && $.isFunction(text.test)) {
                    return text.test(trimmedText);
                } else {
                    return trimmedText.indexOf(text) !== -1;
                }
            },
            toBeCorrectValuesInInputs: function (values) {
                var expected = {
                    name: this.actual.$(SELECTORS.inputName).val(),
                    description: this.actual
                        .$(SELECTORS.inputDescription).val()
                };

                return _.isEqual(values, expected);
            },
            toBeCorrectValuesInModel: function (values) {
                return _.every(values, function (value, key) {
                    return this.actual.get(key) === value;
                }.bind(this));
            }
        });
    });

    afterEach(function() {
        delete window.course;
    });

    describe('GroupConfigurationDetails', function() {
        beforeEach(function() {
            view_helpers.installTemplate('group-configuration-details', true);

            this.model = new GroupConfigurationModel({
                name: 'Configuration',
                description: 'Configuration Description',
                id: 0
            });

            this.collection = new GroupConfigurationCollection([ this.model ]);
            this.view = new GroupConfigurationDetails({
                model: this.model
            });
            appendSetFixtures(this.view.render().el);
        });

        it('should render properly', function() {
            expect(this.view.$el).toContainText('Configuration');
            expect(this.view.$el).toContainText('ID: 0');
        });

        it('should show groups appropriately', function() {
            this.model.get('groups').add([{}]);
            this.model.set('showGroups', false);
            this.view.$('.show-groups').click();

            expect(this.model.get('showGroups')).toBeTruthy();
            expect(this.view.$(SELECTORS.group).length).toBe(3);
            expect(this.view.$(SELECTORS.groupsCount).get(0)).not.toExist();
            expect(this.view.$(SELECTORS.description))
                .toContainText('Configuration Description');
            expect(this.view.$(SELECTORS.groupsAllocation))
                .toContainText('33%');
        });

        it('should hide groups appropriately', function() {
            this.model.get('groups').add([{}]);
            this.model.set('showGroups', true);
            this.view.$('.hide-groups').click();

            expect(this.model.get('showGroups')).toBeFalsy();
            expect(this.view.$(SELECTORS.group).get(0)).not.toExist();
            expect(this.view.$(SELECTORS.groupsCount))
                .toContainText('Contains 3 groups');
            expect(this.view.$(SELECTORS.description).get(0)).not.toExist();
            expect(this.view.$(SELECTORS.groupsAllocation).get(0))
                .not.toExist();
        });
    });

    describe('GroupConfigurationEdit', function() {

        var setValuesToInputs = function (view, values) {
            _.each(values, function (value, selector) {
                if (SELECTORS[selector]) {
                    view.$(SELECTORS[selector]).val(value);
                }
            });
        };

        beforeEach(function() {
            view_helpers.installViewTemplates();
            view_helpers.installTemplate('group-configuration-edit');
            view_helpers.installTemplate('group-edit');

            this.model = new GroupConfigurationModel({
                name: 'Configuration',
                description: 'Configuration Description',
                id: 0,
                editing: true
            });
            this.collection = new GroupConfigurationCollection([this.model]);
            this.collection.url = '/group_configurations';
            this.view = new GroupConfigurationEdit({
                model: this.model
            });
            appendSetFixtures(this.view.render().el);
        });

        it('should render properly', function() {
            expect(this.view).toBeCorrectValuesInInputs({
                name: 'Configuration',
                description: 'Configuration Description'
            });
        });

        it ('should allow you to create new empty groups', function() {
            var numGroups = this.model.get('groups').length;
            this.view.$('.action-add-group').click();
            expect(this.model.get('groups').length).toEqual(numGroups + 1);
            expect(this.model.get('groups').last().isEmpty()).toBeTruthy();
        });

        it('should save properly', function() {
            var requests = create_sinon.requests(this),
                notificationSpy = view_helpers.createNotificationSpy(),
                groups;

            this.model.get('groups').add([{ name: 'Group C' }]);
            setValuesToInputs(this.view, {
                inputName: 'New Configuration',
                inputDescription: 'New Description'
            });

            this.view.$('form').submit();
            view_helpers.verifyNotificationShowing(notificationSpy, /Saving/);
            requests[0].respond(200);
            view_helpers.verifyNotificationHidden(notificationSpy);

            expect(this.model).toBeCorrectValuesInModel({
                name: 'New Configuration',
                description: 'New Description'
            });

            groups = this.model.get('groups');
            expect(groups.length).toBe(3);
            expect(groups.at(2).get('name')).toBe('Group C');
            expect(this.view.$el.get(0)).not.toExist();
        });

        it('does not hide saving message if failure', function() {
            var requests = create_sinon.requests(this),
                notificationSpy = view_helpers.createNotificationSpy();

            setValuesToInputs(this.view, { inputName: 'New Configuration' });
            this.view.$('form').submit();
            view_helpers.verifyNotificationShowing(notificationSpy, /Saving/);
            create_sinon.respondWithError(requests);
            view_helpers.verifyNotificationShowing(notificationSpy, /Saving/);
        });

        it('does not save on cancel', function() {
            this.model.get('groups').add([{ name: 'Group C' }]);
            setValuesToInputs(this.view, {
                inputName: 'New Configuration',
                inputDescription: 'New Description'
            });

            expect(this.model.get('groups').length).toBe(3);

            this.view.$('.action-cancel').click();
            expect(this.model).toBeCorrectValuesInModel({
                name: 'Configuration',
                description: 'Configuration Description'
            });
            // Model is still exist in the collection
            expect(this.collection.indexOf(this.model)).toBeGreaterThan(-1);
            expect(this.collection.length).toBe(1);
            expect(this.model.get('groups').length).toBe(2);
        });

        it('should be removed on cancel if it is a new item', function() {
            spyOn(this.model, 'isNew').andReturn(true);
            setValuesToInputs(this.view, {
                inputName: 'New Configuration',
                inputDescription: 'New Description'
            });
            this.view.$('.action-cancel').click();
            // Model is removed from the collection
            expect(this.collection.length).toBe(0);
        });

        it('should be possible to correct validation errors', function() {
            var requests = create_sinon.requests(this);

            // Set incorrect value
            setValuesToInputs(this.view, { inputName: '' });
            // Try to save
            this.view.$('form').submit();
            // See error message
            expect(this.view.$(SELECTORS.errorMessage)).toContainText(
                'Group Configuration name is required'
            );
            // No request
            expect(requests.length).toBe(0);
            // Set correct value
            setValuesToInputs(this.view, { inputName: 'New Configuration' });
            // Try to save
            this.view.$('form').submit();
            requests[0].respond(200);
            // Model is updated
            expect(this.model).toBeCorrectValuesInModel({
                name: 'New Configuration'
            });
            // Error message disappear
            expect(this.view.$(SELECTORS.errorMessage).get(0)).not.toExist();
            expect(requests.length).toBe(1);
        });

        it('should have appropriate class names on focus/blur', function () {
            var element = this.view.$(SELECTORS.inputName),
                parent = this.view.$('.add-group-configuration-name').get(0),
                groupInput = this.view.$(SELECTORS.inputGroupName).first(),
                groupFields = this.view.$(SELECTORS.groupFields).get(0);

            element.focus();
            expect(parent).toHaveClass('is-focused');
            element.blur();
            expect(parent).not.toHaveClass('is-focused');

            groupInput.focus();
            expect(groupFields).toHaveClass('is-focused');
            groupInput.blur();
            expect(groupFields).not.toHaveClass('is-focused');
        });

        describe('removes all empty groups on cancel', function () {
            it('the model has a non-empty groups', function() {
                var groups = this.model.get('groups');

                this.view.render();
                groups.add([{ name: 'non-empty' }]);
                expect(groups.length).toEqual(3);
                this.view.$('.action-cancel').click();
                expect(groups.length).toEqual(2);
            });

            it('except two if the model has no non-empty groups', function() {
                var groups = this.model.get('groups');

                this.view.render();
                groups.add([{}, {}, {}]);
                expect(groups.length).toEqual(5);
                this.view.$('.action-cancel').click();
                expect(groups.length).toEqual(2);
            });
        });
    });

    describe('GroupConfigurationsList', function() {
        beforeEach(function() {
            view_helpers.installTemplate('no-group-configurations', true);

            this.collection = new GroupConfigurationCollection();
            this.view = new GroupConfigurationsList({
                collection: this.collection
            });
            appendSetFixtures(this.view.render().el);
        });

        describe('empty template', function () {
            it('should be rendered if no group configurations', function() {
                expect(this.view.$el).toContainText(
                    'You haven\'t created any group configurations yet.'
                );
                expect(this.view.$('.new-button').get(0)).toExist();
                expect(this.view.$(SELECTORS.itemView).get(0)).not.toExist();
            });

            it('should disappear if group configuration is added', function() {
                var emptyMessage = 'You haven\'t created any group ' +
                    'configurations yet.';

                expect(this.view.$el).toContainText(emptyMessage);
                expect(this.view.$(SELECTORS.itemView).get(0)).not.toExist();
                this.collection.add([{}]);
                expect(this.view.$el).not.toContainText(emptyMessage);
                expect(this.view.$(SELECTORS.itemView).get(0)).toExist();
            });
        });
    });

    describe('GroupConfigurationItem', function() {
        beforeEach(function() {
            view_helpers.installTemplate('group-configuration-edit', true);
            view_helpers.installTemplate('group-configuration-details');
            this.model = new GroupConfigurationModel({ id: 0 });
            this.collection = new GroupConfigurationCollection([ this.model ]);
            this.view = new GroupConfigurationItem({
                model: this.model
            });
            appendSetFixtures(this.view.render().el);
        });

        it('should render properly', function() {
            // Details view by default
            expect(this.view.$(SELECTORS.detailsView).get(0)).toExist();
            this.view.$('.action-edit .edit').click();
            expect(this.view.$(SELECTORS.editView).get(0)).toExist();
            expect(this.view.$(SELECTORS.detailsView).get(0)).not.toExist();
            this.view.$('.action-cancel').click();
            expect(this.view.$(SELECTORS.detailsView).get(0)).toExist();
            expect(this.view.$(SELECTORS.editView).get(0)).not.toExist();
        });
    });

    describe('GroupEdit', function() {
        beforeEach(function() {
            view_helpers.installTemplate('group-edit', true);

            this.model = new GroupModel({
                name: 'Group A'
            });

            this.collection = new GroupCollection([this.model]);

            this.view = new GroupEdit({
                model: this.model
            });
        });

        describe('Basic', function () {
            it('can render properly', function() {
                this.view.render();
                expect(this.view.$('.group-name').val()).toBe('Group A');
                expect(this.view.$('.group-allocation')).toContainText('100%');
            });

            it ('can delete itself', function() {
                this.view.render().$('.action-close').click();
                expect(this.collection.length).toEqual(0);
            });
        });

        describe('getGroupId', function () {
            var view, injector, mockGettext, initializeGroupEdit;

            mockGettext = function (returnedValue) {
                var injector = new Squire();

                injector.mock('gettext', function () {
                    return function () { return returnedValue; };
                });

                return injector;
            };

            initializeGroupEdit = function (dict, model, that) {
                runs(function() {
                    injector = mockGettext(dict);
                    injector.require(['js/views/group_edit'],
                    function(GroupEdit) {
                        view = new GroupEdit({
                            model: model
                        });
                    });
                });

                waitsFor(function() {
                    return view;
                }, 'GroupEdit was not instantiated', 500);

                that.after(function () {
                    view = null;
                    injector.clean();
                    injector.remove();
                });
            };

            it('returns correct ids', function () {
                expect(this.view.getGroupId(0)).toBe('A');
                expect(this.view.getGroupId(1)).toBe('B');
                expect(this.view.getGroupId(25)).toBe('Z');
                expect(this.view.getGroupId(702)).toBe('AAA');
                expect(this.view.getGroupId(704)).toBe('AAC');
                expect(this.view.getGroupId(475253)).toBe('ZZZZ');
                expect(this.view.getGroupId(475254)).toBe('AAAAA');
                expect(this.view.getGroupId(475279)).toBe('AAAAZ');
            });

            it('just 1 character in the dictionary', function () {
                initializeGroupEdit('1', this.model, this);
                runs(function() {
                    expect(view.getGroupId(0)).toBe('1');
                    expect(view.getGroupId(1)).toBe('11');
                    expect(view.getGroupId(5)).toBe('111111');
                });
            });

            it('allow to use unicode characters in the dict', function () {
                initializeGroupEdit('ö诶úeœ', this.model, this);
                runs(function() {
                    expect(view.getGroupId(0)).toBe('ö');
                    expect(view.getGroupId(1)).toBe('诶');
                    expect(view.getGroupId(5)).toBe('öö');
                    expect(view.getGroupId(29)).toBe('œœ');
                    expect(view.getGroupId(30)).toBe('ööö');
                    expect(view.getGroupId(43)).toBe('öúe');
                });
            });

            it('return initial value if dictionary is empty', function () {
                initializeGroupEdit('', this.model, this);
                runs(function() {
                    expect(view.getGroupId(0)).toBe('0');
                    expect(view.getGroupId(5)).toBe('5');
                    expect(view.getGroupId(30)).toBe('30');
                });
            });
        });
    });
});


