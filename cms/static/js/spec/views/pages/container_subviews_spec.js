define(["jquery", "underscore", "underscore.string", "js/spec_helpers/create_sinon", "js/spec_helpers/edit_helpers",
    "js/views/feedback_prompt", "js/views/pages/container", "js/views/pages/container_subviews",
    "js/models/xblock_info"],
    function ($, _, str, create_sinon, edit_helpers, Prompt, ContainerPage, ContainerSubviews, XBlockInfo) {

        describe("Container Subviews", function() {
            var model, containerPage, requests, renderContainerPage, respondWithHtml, respondWithJson, fetch,
                disabledCss = "is-disabled",
                mockContainerPage = readFixtures('mock/mock-container-page.underscore'),
                mockContainerXBlockHtml = readFixtures('mock/mock-empty-container-xblock.underscore');

            beforeEach(function () {
                edit_helpers.installTemplate('xblock-string-field-editor');
                edit_helpers.installTemplate('publish-xblock');
                appendSetFixtures(mockContainerPage);

                model = new XBlockInfo({
                    id: 'locator-container',
                    display_name: 'Test Container',
                    category: 'vertical',
                    published: false,
                    has_changes: false
                });
                containerPage = new ContainerPage({
                    model: model,
                    templates: edit_helpers.mockComponentTemplates,
                    el: $('#content'),
                    isUnitPage: true
                });
            });

            renderContainerPage = function(html, that) {
                requests = create_sinon.requests(that);
                containerPage.render();
                respondWithHtml(html);
            };

            respondWithHtml = function(html) {
                var requestIndex = requests.length - 1;
                create_sinon.respondWithJson(
                    requests,
                    { html: html, "resources": [] },
                    requestIndex
                );
            };

            respondWithJson = function(json, requestIndex) {
                create_sinon.respondWithJson(
                    requests,
                    json,
                    requestIndex
                );
            };

            fetch = function (json) {
                model.fetch();
                respondWithJson(json);
            };

            describe("PreviewActionController", function () {
                var viewPublishedCss = '.view-button',
                    previewCss = '.preview-button';

                it('renders correctly for private unit', function () {
                    renderContainerPage(mockContainerXBlockHtml, this);
                    expect(containerPage.$(viewPublishedCss)).toHaveClass(disabledCss);
                    expect(containerPage.$(previewCss)).not.toHaveClass(disabledCss);
                });

                it('updates when published attribute changes', function () {
                    renderContainerPage(mockContainerXBlockHtml, this);
                    fetch({"id": "locator-container", "published": true});
                    expect(containerPage.$(viewPublishedCss)).not.toHaveClass(disabledCss);

                    fetch({"id": "locator-container", "published": false});
                    expect(containerPage.$(viewPublishedCss)).toHaveClass(disabledCss);
                });

                it('updates when has_changes attribute changes', function () {
                    renderContainerPage(mockContainerXBlockHtml, this);
                    fetch({"id": "locator-container", "has_changes": true});
                    expect(containerPage.$(previewCss)).not.toHaveClass(disabledCss);

                    fetch({"id": "locator-container", "published": true, "has_changes": false});
                    expect(containerPage.$(previewCss)).toHaveClass(disabledCss);

                    // If published is false, preview is always enabled.
                    fetch({"id": "locator-container", "published": false, "has_changes": false});
                    expect(containerPage.$(previewCss)).not.toHaveClass(disabledCss);
                });
            });

            describe("VisibilityStateController", function () {
                var unitVisibilityCss = '.section-item.editing a';

                it('renders initially as private with unpublished content', function () {
                    renderContainerPage(mockContainerXBlockHtml, this);
                    expect(containerPage.$(unitVisibilityCss)).toHaveClass('private-item');
                });

                it('renders as public when published and no changes', function () {
                    renderContainerPage(mockContainerXBlockHtml, this);
                    fetch({"id": "locator-container", "published": true, "has_changes": false});
                    expect(containerPage.$(unitVisibilityCss)).toHaveClass('public-item');
                });

                it('renders as draft when published and changes', function () {
                    renderContainerPage(mockContainerXBlockHtml, this);
                    fetch({"id": "locator-container", "published": true, "has_changes": true});
                    expect(containerPage.$(unitVisibilityCss)).toHaveClass('draft-item');
                });

                it('renders as private when not published', function () {
                    renderContainerPage(mockContainerXBlockHtml, this);
                    fetch({"id": "locator-container", "published": false, "has_changes": true});
                    expect(containerPage.$(unitVisibilityCss)).toHaveClass('private-item');

                    fetch({"id": "locator-container", "published": false, "has_changes": false});
                    expect(containerPage.$(unitVisibilityCss)).toHaveClass('private-item');

                    fetch({"id": "locator-container", "published": false});
                    expect(containerPage.$(unitVisibilityCss)).toHaveClass('private-item');
                });
            });

            describe("Publisher", function () {
                var headerCss = '.pub-status',
                    bitPublishingCss = "div.bit-publishing",
                    publishedBit = "published",
                    draftBit = "draft",
                    publishButtonCss = ".action-publish",
                    discardChangesButtonCss = ".action-discard",
                    request, lastRequest, promptSpies, sendDiscardChangesToServer;

                lastRequest = function() { return requests[requests.length - 1]; };

                sendDiscardChangesToServer = function(test) {
                    // Helper function to do the discard operation, up until the server response.
                    renderContainerPage(mockContainerXBlockHtml, test);
                    fetch({"id": "locator-container", "published": true, "has_changes": true});
                    expect(containerPage.$(discardChangesButtonCss)).not.toHaveClass('is-disabled');
                    expect(containerPage.$(bitPublishingCss)).toHaveClass(draftBit);
                    // Click discard changes
                    containerPage.$(discardChangesButtonCss).click();

                    // Confirm the discard.
                    expect(promptSpies.constructor).toHaveBeenCalled();
                    promptSpies.constructor.mostRecentCall.args[0].actions.primary.click(promptSpies);

                    request = lastRequest();
                    expect(request.url).toEqual("/xblock/locator-container");
                    expect(request.method).toEqual("POST");
                    expect(JSON.parse(request.requestBody).publish).toEqual("discard_changes");
                };

                beforeEach(function() {
                    promptSpies = spyOnConstructor(Prompt, "Warning", ["show", "hide"]);
                    promptSpies.show.andReturn(this.promptSpies);
                });

                it('renders correctly with private content', function () {
                    var verifyPrivateState = function(){
                        // State is the same regardless of "has_changes" value.
                        expect(containerPage.$(headerCss).text()).toContain('Draft (Unpublished changes)');
                        expect(containerPage.$(publishButtonCss)).not.toHaveClass(disabledCss);
                        expect(containerPage.$(discardChangesButtonCss)).toHaveClass(disabledCss);
                        expect(containerPage.$(bitPublishingCss)).toHaveClass(draftBit);
                    };
                    renderContainerPage(mockContainerXBlockHtml, this);
                    fetch({"id": "locator-container", "published": false, "has_changes": false});
                    verifyPrivateState();

                    fetch({"id": "locator-container", "published": false, "has_changes": true});
                    verifyPrivateState();
                });

                it('renders correctly with public content', function () {
                    renderContainerPage(mockContainerXBlockHtml, this);
                    fetch({"id": "locator-container", "published": true, "has_changes": false});
                    expect(containerPage.$(headerCss).text()).toContain('Published');
                    expect(containerPage.$(publishButtonCss)).toHaveClass(disabledCss);
                    expect(containerPage.$(discardChangesButtonCss)).toHaveClass(disabledCss);
                    expect(containerPage.$(bitPublishingCss)).toHaveClass(publishedBit);

                    fetch({"id": "locator-container", "published": true, "has_changes": true});
                    expect(containerPage.$(headerCss).text()).toContain('Draft (Unpublished changes)');
                    expect(containerPage.$(publishButtonCss)).not.toHaveClass(disabledCss);
                    expect(containerPage.$(discardChangesButtonCss)).not.toHaveClass(disabledCss);
                    expect(containerPage.$(bitPublishingCss)).toHaveClass(draftBit);
                });

                it('can publish private content', function () {
                    var notificationSpy = edit_helpers.createNotificationSpy();
                    renderContainerPage(mockContainerXBlockHtml, this);
                    fetch({"id": "locator-container", "published": false, "has_changes": false});
                    expect(containerPage.$(bitPublishingCss)).toHaveClass(draftBit);

                    // Click publish
                    containerPage.$(publishButtonCss).click();
                    edit_helpers.verifyNotificationShowing(notificationSpy, /Publishing/);

                    request = lastRequest();
                    expect(request.url).toEqual("/xblock/locator-container");
                    expect(request.method).toEqual("POST");
                    expect(JSON.parse(request.requestBody).publish).toEqual("make_public");

                    // Response to publish call
                    respondWithJson({"id": "locator-container", "published": true, "has_changes": false});
                    edit_helpers.verifyNotificationHidden(notificationSpy);

                    request = lastRequest();
                    expect(request.url).toEqual("/xblock/locator-container");
                    expect(request.method).toEqual("GET");
                    expect(request.requestBody).toEqual(null);
                    // Response to fetch
                    respondWithJson({"id": "locator-container", "published": true, "has_changes": false});

                    // Verify updates displayed
                    expect(containerPage.$(bitPublishingCss)).toHaveClass(publishedBit);
                    // Verify that the "published" value has been cleared out of the model.
                    expect(containerPage.model.get("publish")).toBeNull();
                });

                it('can does not fetch if publish fails', function () {
                    renderContainerPage(mockContainerXBlockHtml, this);
                    fetch({"id": "locator-container", "published": false, "has_changes": false});
                    expect(containerPage.$(bitPublishingCss)).toHaveClass(draftBit);

                    // Click publish
                    containerPage.$(publishButtonCss).click();

                    var numRequests = requests.length;
                    // Respond with failure
                    create_sinon.respondWithError(requests);

                    expect(requests.length).toEqual(numRequests);

                    // Verify still in draft state.
                    expect(containerPage.$(bitPublishingCss)).toHaveClass(draftBit);
                    // Verify that the "published" value has been cleared out of the model.
                    expect(containerPage.model.get("publish")).toBeNull();
                });

                it('can discard changes', function () {
                    var notificationSpy = edit_helpers.createNotificationSpy(),
                        renderPageSpy = spyOn(containerPage.xblockPublisher, 'renderPage').andCallThrough(),
                        numRequests;

                    sendDiscardChangesToServer(this);
                    numRequests = requests.length;

                    // Respond with success.
                    respondWithJson({"id": "locator-container", "published": true, "has_changes": false});
                    edit_helpers.verifyNotificationHidden(notificationSpy);

                    // Verify other requests are sent to the server to update page state.
                    // Response to fetch, specifying the very next request (as multiple requests will be sent to server)
                    expect(requests.length > numRequests).toBeTruthy();
                    expect(containerPage.model.get("publish")).toBeNull();
                    expect(renderPageSpy).toHaveBeenCalled();
                });

                it('does not fetch if discard changes fails', function () {
                    var renderPageSpy = spyOn(containerPage.xblockPublisher, 'renderPage').andCallThrough(),
                        numRequests;

                    sendDiscardChangesToServer(this);
                    numRequests = requests.length;

                    // Respond with failure
                    create_sinon.respondWithError(requests);

                    expect(requests.length).toEqual(numRequests);
                    expect(containerPage.$(discardChangesButtonCss)).not.toHaveClass('is-disabled');
                    expect(containerPage.model.get("publish")).toBeNull();
                    expect(renderPageSpy).not.toHaveBeenCalled();
                });

                it('does not discard changes on cancel', function () {
                    renderContainerPage(mockContainerXBlockHtml, this);
                    fetch({"id": "locator-container", "published": true, "has_changes": true});
                    var numRequests = requests.length;

                    // Click discard changes
                    containerPage.$(discardChangesButtonCss).click();

                    // Click cancel to confirmation.
                    expect(promptSpies.constructor).toHaveBeenCalled();
                    promptSpies.constructor.mostRecentCall.args[0].actions.secondary.click(promptSpies);

                    expect(requests.length).toEqual(numRequests);
                    expect(containerPage.$(discardChangesButtonCss)).not.toHaveClass('is-disabled');
                });
            });
        });
    });
