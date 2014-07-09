/**
 * Subviews (usually small side panels) for XBlockContainerPage.
 */
define(["jquery", "underscore", "gettext", "js/views/baseview", "js/views/feedback_prompt"],
    function ($, _, gettext, BaseView, PromptView) {

        var disabledCss = "is-disabled";

        /**
         * A view that calls render when "has_changes" or "published" values in XBlockInfo have changed
         * after a server sync operation.
         */
        var UnitStateListenerView =  BaseView.extend({

            // takes XBlockInfo as a model
            initialize: function() {
                this.model.on('sync', this.onSync, this);
            },

            onSync: function(e) {
                if (e.changedAttributes() &&
                    (('has_changes' in e.changedAttributes()) || ('published' in e.changedAttributes()))) {
                   this.render();
                }
            },

            render: function() {}
        });

        /**
         * A controller for updating the visibility status of the unit on the RHS navigation tree.
         */
        var VisibilityStateController = UnitStateListenerView.extend({

            render: function() {
                var computeState = function(published, has_changes) {
                    if (!published) {
                        return "private";
                    }
                    else if (has_changes) {
                        return "draft";
                    }
                    else {
                        return "public";
                    }
                };
                var state = computeState(this.model.get('published'), this.model.get('has_changes'));
                this.$el.removeClass("private-item public-item draft-item");
                this.$el.addClass(state + "-item");
            }
        });

        /**
         * A controller for updating the "View Live" and "Preview" buttons.
         */
        var PreviewActionController = UnitStateListenerView.extend({

            render: function() {
                var previewAction = this.$el.find('.preview-button'),
                    viewLiveAction = this.$el.find('.view-button');
                if (this.model.get('published')) {
                    viewLiveAction.removeClass(disabledCss);
                }
                else {
                    viewLiveAction.addClass(disabledCss);
                }
                if (this.model.get('has_changes') || !this.model.get('published')) {
                    previewAction.removeClass(disabledCss);
                }
                else {
                    previewAction.addClass(disabledCss);
                }
            }
        });

        /**
         * Publisher is a view that supports the following:
         * 1) Publishing of a draft version of an xblock.
         * 2) Discarding of edits in a draft version.
         * 3) Display of who last edited the xblock, and when.
         * 4) Display of publish status (published, published with changes, changes with no published version).
         */
        var Publisher = BaseView.extend({
            events: {
                'click .action-publish': 'publish',
                'click .action-discard': 'discardChanges'
            },

            // takes XBlockInfo as a model

            initialize: function () {
                BaseView.prototype.initialize.call(this);
                this.template = this.loadTemplate('publish-xblock');
                this.model.on('sync', this.onSync, this);
                this.renderPage = this.options.renderPage;
            },

            onSync: function(e) {
                if (e.changedAttributes() &&
                    (('has_changes' in e.changedAttributes()) || ('published' in e.changedAttributes()) ||
                    ('subtree_edited_on' in e.changedAttributes()) || ('subtree_edited_by' in e.changedAttributes()))) {
                   this.render();
                }
            },

            render: function () {
                this.$el.html(this.template({
                    has_changes: this.model.get('has_changes'),
                    published: this.model.get('published'),
                    subtree_edited_on: this.model.get('subtree_edited_on'),
                    subtree_edited_by: this.model.get('subtree_edited_by'),
                    published_on: this.model.get('published_on'),
                    published_by: this.model.get('published_by')
                }));

                return this;
            },

            publish: function (e) {
                var xblockInfo = this.model;
                if (e && e.preventDefault) {
                    e.preventDefault();
                }
                this.runOperationShowingMessage(gettext('Publishing&hellip;'),
                    function () {
                        return xblockInfo.save({publish: 'make_public'});
                    }).always(function() {
                        xblockInfo.set("publish", null);
                    }).done(function () {
                        xblockInfo.fetch();
                    });
            },

            discardChanges: function (e) {
                if (e && e.preventDefault) {
                    e.preventDefault();
                }
                var xblockInfo = this.model, view, renderPage = this.renderPage;

                view = new PromptView.Warning({
                    title: gettext("Discard Changes"),
                    message: gettext("Are you sure you want to discard changes and revert to the last published version?"),
                    actions: {
                        primary: {
                            text: gettext("Discard Changes"),
                            click: function (view) {
                                view.hide();
                                $.ajax({
                                    type: 'DELETE',
                                    url: xblockInfo.url()
                                }).success(function () {
                                    window.alert("Refresh the page to see that changes were discarded. " +
                                        "Auto-refresh will be implemented in a later story.");
                                    /* Fetch is never returning on sandbox-- try
                                       doing a PUT instead of a DELETE with publish option
                                       to work around, or contact dev ops.
                                       STUD-1860
                                    window.crazyAjaxHandler = xblockInfo.fetch({
                                        complete: function(a, b, c) {
                                            debugger;
                                        }
                                    });
                                    renderPage();
                                    */
                                });
                            }
                        },
                        secondary: {
                            text: gettext("Cancel"),
                            click: function (view) {
                                view.hide();
                            }
                        }
                    }
                }).show();
            }
        });

        /**
         * PublishHistory displays when and by whom the xblock was last published, if it ever was.
         */
        var PublishHistory = BaseView.extend({
            // takes XBlockInfo as a model

            initialize: function () {
                BaseView.prototype.initialize.call(this);
                this.template = this.loadTemplate('publish-history');
                this.model.on('sync', this.onSync, this);
            },

            onSync: function(e) {
                if (e.changedAttributes() && (('published' in e.changedAttributes()) ||
                    ('published_on' in e.changedAttributes()) || ('published_by' in e.changedAttributes()))) {
                   this.render();
                }
            },

            render: function () {
                this.$el.html(this.template({
                    published: this.model.get('published'),
                    published_on: this.model.get('published_on'),
                    published_by: this.model.get('published_by')
                }));

                return this;
            }
        });

        return {
            'VisibilityStateController': VisibilityStateController,
            'PreviewActionController': PreviewActionController,
            'Publisher': Publisher,
            'PublishHistory': PublishHistory
        };
    }); // end define();
