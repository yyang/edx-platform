
from bok_choy.promise import EmptyPromise


class CommonMixin(object):
    """
    Common Functionality
    """

    def _wait_for_element(self, element_selector, promise_desc):
        """
        Wait for element specified by `element_selector` is present in DOM.

        Arguments:
            element_selector (str): css selector of the element.
            promise_desc (str): Description of the Promise, used in log messages.

        """
        def _is_element_present():
            """
            Check if web-element present in DOM.

            Returns:
                bool: Tells elements presence.

            """
            return self.q(css=element_selector).present

        EmptyPromise(_is_element_present, promise_desc, timeout=200).fulfill()

    def _wait_for_element_visibility(self, element_selector, promise_desc):
        """
        Wait for an element to be visible.

        Arguments:
            element_selector (str): css selector of the element.
            promise_desc (str): Description of the Promise, used in log messages.

        """
        def _is_element_visible():
            """
            Check if a web-element is visible.

            Returns:
                bool: Tells element visibility status.

            """
            return self.q(css=element_selector).visible

        EmptyPromise(_is_element_visible, promise_desc, timeout=200).fulfill()
