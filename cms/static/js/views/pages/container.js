/**
 * XBlockContainerPage is used to display Studio's container page for an xblock which has children.
 * This page allows the user to understand and manipulate the xblock and its children.
 */
define(["jquery", "underscore", "gettext", "js/views/baseview", "js/views/container",
        "js/views/xblock", "js/views/components/add_xblock", "js/views/modals/edit_xblock", "js/models/xblock_info",
        "js/views/xblock_string_field_editor", "js/views/pages/container_subviews"],
    function ($, _, gettext, BaseView, ContainerView, XBlockView, AddXBlockComponent, EditXBlockModal, XBlockInfo,
                XBlockStringFieldEditor, ContainerSubviews) {
        var XBlockContainerPage = BaseView.extend({
            // takes XBlockInfo as a model

            view: 'container_preview',

            initialize: function(options) {
                BaseView.prototype.initialize.call(this);
                this.nameEditor = new XBlockStringFieldEditor({
                    el: this.$('.wrapper-xblock-field'),
                    model: this.model
                });
                this.nameEditor.render();
                this.xblockView = new ContainerView({
                    el: this.$('.wrapper-xblock'),
                    model: this.model,
                    view: this.view
                });
                this.isUnitPage = this.options.isUnitPage;
                if (this.isUnitPage) {
                    this.xblockPublisher = new ContainerSubviews.Publisher({
                        el: this.$('#publish-unit'),
                        model: this.model,
                        // When "Discard Changes" is clicked, the whole page must be re-rendered.
                        renderPage: this.render
                    });
                    this.xblockPublisher.render();

                    this.publishHistory = new ContainerSubviews.PublishHistory({
                        el: this.$('#publish-history'),
                        model: this.model
                    });
                    this.publishHistory.render();

                    // No need to render initially. This is only used for updating state
                    // when the unit changes visibility.
                    this.visibilityState = new ContainerSubviews.VisibilityStateController({
                        el: this.$('.section-item.editing a'),
                        model: this.model
                    });
                    this.previewActions = new ContainerSubviews.PreviewActionController({
                        el: this.$('.nav-actions'),
                        model: this.model
                    });
                    this.previewActions.render();
                }
            },

            render: function(options) {
                var self = this,
                    xblockView = this.xblockView,
                    loadingElement = this.$('.ui-loading'),
                    unitLocationTree = this.$('.unit-location'),
                    hiddenCss='is-hidden';

                loadingElement.removeClass(hiddenCss);

                // Hide both blocks until we know which one to show
                xblockView.$el.addClass(hiddenCss);

                if (!options || !options.refresh) {
                    // Add actions to any top level buttons, e.g. "Edit" of the container itself.
                    // Do not add the actions on "refresh" though, as the handlers are already registered.
                    self.addButtonActions(this.$el);
                }

                // Render the xblock
                xblockView.render({
                    success: function() {
                        xblockView.xblock.runtime.notify("page-shown", self);
                        xblockView.$el.removeClass(hiddenCss);
                        self.renderAddXBlockComponents();
                        self.onXBlockRefresh(xblockView);
                        self.refreshDisplayName();
                        loadingElement.addClass(hiddenCss);
                        unitLocationTree.removeClass(hiddenCss);
                        self.delegateEvents();
                    }
                });
            },

            findXBlockElement: function(target) {
                return $(target).closest('.studio-xblock-wrapper');
            },

            getURLRoot: function() {
                return this.xblockView.model.urlRoot;
            },

            refreshDisplayName: function() {
                var displayName = this.$('.xblock-header .header-details .xblock-display-name').first().text().trim();
                this.model.set('display_name', displayName);
            },

            onXBlockRefresh: function(xblockView) {
                this.addButtonActions(xblockView.$el);
                this.xblockView.refresh();
                // Update publish and last modified information from the server.
                this.model.fetch();
            },

            renderAddXBlockComponents: function() {
                var self = this;
                this.$('.add-xblock-component').each(function(index, element) {
                    var component = new AddXBlockComponent({
                        el: element,
                        createComponent: _.bind(self.createComponent, self),
                        collection: self.options.templates
                    });
                    component.render();
                });
            },

            addButtonActions: function(element) {
                var self = this;
                element.find('.edit-button').click(function(event) {
                    event.preventDefault();
                    self.editComponent(self.findXBlockElement(event.target));
                });
                element.find('.duplicate-button').click(function(event) {
                    event.preventDefault();
                    self.duplicateComponent(self.findXBlockElement(event.target));
                });
                element.find('.delete-button').click(function(event) {
                    event.preventDefault();
                    self.deleteComponent(self.findXBlockElement(event.target));
                });
            },

            editComponent: function(xblockElement) {
                var self = this,
                    modal = new EditXBlockModal({ });
                modal.edit(xblockElement, this.model, {
                    refresh: function() {
                        self.refreshXBlock(xblockElement);
                    }
                });
            },

            createComponent: function(template, target) {
                // A placeholder element is created in the correct location for the new xblock
                // and then onNewXBlock will replace it with a rendering of the xblock. Note that
                // for xblocks that can't be replaced inline, the entire parent will be refreshed.
                var parentElement = this.findXBlockElement(target),
                    parentLocator = parentElement.data('locator'),
                    buttonPanel = target.closest('.add-xblock-component'),
                    listPanel = buttonPanel.prev(),
                    scrollOffset = this.getScrollOffset(buttonPanel),
                    placeholderElement = $('<div class="studio-xblock-wrapper"></div>').appendTo(listPanel),
                    requestData = _.extend(template, {
                        parent_locator: parentLocator
                    });
                return $.postJSON(this.getURLRoot() + '/', requestData,
                    _.bind(this.onNewXBlock, this, placeholderElement, scrollOffset))
                    .fail(function() {
                        // Remove the placeholder if the update failed
                        placeholderElement.remove();
                    });
            },

            duplicateComponent: function(xblockElement) {
                // A placeholder element is created in the correct location for the duplicate xblock
                // and then onNewXBlock will replace it with a rendering of the xblock. Note that
                // for xblocks that can't be replaced inline, the entire parent will be refreshed.
                var self = this,
                    parent = xblockElement.parent();
                this.runOperationShowingMessage(gettext('Duplicating&hellip;'),
                    function() {
                        var scrollOffset = self.getScrollOffset(xblockElement),
                            placeholderElement = $('<div class="studio-xblock-wrapper"></div>').insertAfter(xblockElement),
                            parentElement = self.findXBlockElement(parent),
                            requestData = {
                                duplicate_source_locator: xblockElement.data('locator'),
                                parent_locator: parentElement.data('locator')
                            };
                        return $.postJSON(self.getURLRoot() + '/', requestData,
                            _.bind(self.onNewXBlock, self, placeholderElement, scrollOffset))
                            .fail(function() {
                                // Remove the placeholder if the update failed
                                placeholderElement.remove();
                            });
                    });
            },

            deleteComponent: function(xblockElement) {
                var self = this;
                this.confirmThenRunOperation(gettext('Delete this component?'),
                    gettext('Deleting this component is permanent and cannot be undone.'),
                    gettext('Yes, delete this component'),
                    function() {
                        self.runOperationShowingMessage(gettext('Deleting&hellip;'),
                            function() {
                                return $.ajax({
                                    type: 'DELETE',
                                    url: self.getURLRoot() + "/" +
                                        xblockElement.data('locator')
                                }).success(_.bind(self.onDelete, self, xblockElement));
                            });
                    });
            },

            onDelete: function(xblockElement) {
                // get the parent so we can remove this component from its parent.
                var xblockView = this.xblockView,
                    xblock = xblockView.xblock,
                    parent = this.findXBlockElement(xblockElement.parent());
                xblockElement.remove();
                xblockView.updateChildren(parent);
                xblock.runtime.notify('deleted-child', parent.data('locator'));
                // Update publish and last modified information from the server.
                this.model.fetch();
            },

            onNewXBlock: function(xblockElement, scrollOffset, data) {
                this.setScrollOffset(xblockElement, scrollOffset);
                xblockElement.data('locator', data.locator);
                return this.refreshXBlock(xblockElement);
            },

            /**
             * Refreshes the specified xblock's display. If the xblock is an inline child of a
             * reorderable container then the element will be refreshed inline. If not, then the
             * parent container will be refreshed instead.
             * @param element An element representing the xblock to be refreshed.
             */
            refreshXBlock: function(element) {
                var xblockElement = this.findXBlockElement(element),
                    parentElement = xblockElement.parent(),
                    rootLocator = this.xblockView.model.id;
                if (xblockElement.length === 0 || xblockElement.data('locator') === rootLocator) {
                    this.render({refresh: true});
                } else if (parentElement.hasClass('reorderable-container')) {
                    this.refreshChildXBlock(xblockElement);
                } else {
                    this.refreshXBlock(this.findXBlockElement(parentElement));
                }
            },

            /**
             * Refresh an xblock element inline on the page, using the specified xblockInfo.
             * Note that the element is removed and replaced with the newly rendered xblock.
             * @param xblockElement The xblock element to be refreshed.
             * @returns {promise} A promise representing the complete operation.
             */
            refreshChildXBlock: function(xblockElement) {
                var self = this,
                    xblockInfo,
                    TemporaryXBlockView,
                    temporaryView;
                xblockInfo = new XBlockInfo({
                    id: xblockElement.data('locator')
                });
                // There is only one Backbone view created on the container page, which is
                // for the container xblock itself. Any child xblocks rendered inside the
                // container do not get a Backbone view. Thus, create a temporary view
                // to render the content, and then replace the original element with the result.
                TemporaryXBlockView = XBlockView.extend({
                    updateHtml: function(element, html) {
                        // Replace the element with the new HTML content, rather than adding
                        // it as child elements.
                        this.$el = $(html).replaceAll(element);
                    }
                });
                temporaryView = new TemporaryXBlockView({
                    model: xblockInfo,
                    view: 'reorderable_container_child_preview',
                    el: xblockElement
                });
                return temporaryView.render({
                    success: function() {
                        self.onXBlockRefresh(temporaryView);
                        temporaryView.unbind();  // Remove the temporary view
                    }
                });
            }
        });

        return XBlockContainerPage;
    }); // end define();
