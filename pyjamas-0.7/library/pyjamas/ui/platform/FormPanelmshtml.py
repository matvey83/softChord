class FormPanel(SimplePanel):
    # FormPanelImpl.hookEvents
    def hookEvents(self, iframe, form, listener):
        # TODO: might have to fix this, use DOM.set_listener()
        self._listener = listener
        if iframe:
            mf = get_main_frame()
            self._onload_listener = mf.addEventListener(iframe, "readystatechange",
                                                        self._onload)

        self._onsubmit_listener = mf.addEventListener(form, "submit",
                                                    self._onsubmit)

    # FormPanelImpl.unhookEvents
    def unhookEvents(self, iframe, form):
        iframe.onreadystatechange = None
        form.onsubmit = None

