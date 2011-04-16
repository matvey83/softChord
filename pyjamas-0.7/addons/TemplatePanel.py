from __pyjamas__ import unescape
from RichTextEditor import RichTextEditor
from pyjamas import Window
from __pyjamas__ import encodeURIComponent
from EventDelegate import EventDelegate
from pyjamas.ui.Label import Label
from pyjamas.ui.ComplexPanel import ComplexPanel
from __pyjamas__ import console
from pyjamas.HTTPRequest import HTTPRequest
from pyjamas.ui.HTML import HTML
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas import DOM


class TemplateLoader:
    def __init__(self, panel, url):
        self.panel = panel

    def onCompletion(self, text):
        self.panel.setTemplateText(text)

    def onError(self, text, code):
        self.panel.onError(text, code)

    def onTimeout(self, text):
        self.panel.onTimeout(text)


class ContentSaveHandler:
    def __init__(self, templatePanel):
        self.templatePanel = templatePanel

    def onCompletion(self):
        self.templatePanel.onSaveComplete()

    def onError(self, error):
        Window.alert("Save failed: "+error)


class PendingAttachOrInsert:
    def __init__(self, name, widget):
        self.name = name
        self.widget = widget


class TemplatePanel(ComplexPanel):
    """
    Panel which allows you to attach or insert widgets into a
    pre-defined template.

    We don't do any caching of our own, since the browser will do
    caching for us, and probably more efficiently.
    """
    templateRoot = ""
    # XXX What is this text expression supposed to do? It won't be
    # added to the docstring as it is.
    """Set staticRoot to change the base path of all the templates
    that are loaded; templateRoot should have a trailing slash"""

    def __init__(self, templateName, allowEdit=False):
        ComplexPanel.__init__(self)
        self.loaded = False # Set after widgets are attached
        self.widgetsAttached = False
        self.id = None
        self.templateName = None
        self.title = None
        self.elementsById = {}
        self.metaTags = {}
        self.body = None
        self.links = []
        self.forms = []
        self.metaTagList = []
        self.loadListeners = []
        self.toAttach = []
        self.toInsert = []
        self.setElement(DOM.createDiv())
        self.editor = None
        self.allowEdit = allowEdit
        if templateName:
            self.loadTemplate(templateName)

    def getTemplatePath(self, templateName):
        return self.templateRoot+'tpl/'+templateName+'.html'

    def loadTemplate(self, templateName):
        self.templateName = templateName
        self.id = templateName + str(hash(self))
        self.httpReq = HTTPRequest()
        self.httpReq.asyncGet(self.getTemplatePath(templateName),
                              TemplateLoader(self))

    def getCurrentTemplate(self):
        """Return the template that is currently loaded, or is loading."""
        return self.templateName

    def isLoaded(self):
        """Return True if the template is finished loading."""
        return self.loaded

    def areWidgetsAttached(self):
        """Return True if the template is loaded and attachWidgets()
        has been called."""
        return self.widgetsAttached

    def setTemplateText(self, text):
        """
        Set the template text; if the template is not HTML, a subclass
        could override this to pre-process the text into HTML before
        passing it to the default implementation.
        """
        if self.allowEdit:
            self.originalText = text
        # If we have children, remove them all first since we are
        # trashing their DOM
        for child in List(self.children):
            self.remove(child)

        DOM.setInnerHTML(self.getElement(), text)
        self.elementsById = {}
        self.links = []
        self.metaTags = {}
        self.forms = []
        self.metaTagList = []

        # Make the ids unique and store a pointer to each named element
        for node in DOM.walkChildren(self.getElement()):
            #console.log("Passing node with name %s", node.nodeName)
            if node.nodeName == "META":
                name = node.getAttribute("name")
                content = node.getAttribute("content")
                console.log("Found meta %o name %s content %s",
                            node, name, content)
                self.metaTags[name] = content
                self.metaTagList.append(node)
            elif node.nodeName == "BODY":
                self.body = node
            elif node.nodeName == "TITLE":
                self.title = DOM.getInnerText(node)
            elif node.nodeName == "FORM":
                self.forms.append(node)

            nodeId = DOM.getAttribute(node, "id")
            if nodeId:
                self.elementsById[nodeId] = node
                DOM.setAttribute(node, "id", self.id + ":" + node.id)
            nodeHref = DOM.getAttribute(node, "href")
            if nodeHref:
                self.links.append(node)

        self.loaded = True
        if self.attached:
            self.attachWidgets()
            self.widgetsAttached = True

        if self.allowEdit:
            self.editor = None
            self.editButton = Label("edit "+unescape(self.templateName))
            self.editButton.addStyleName("link")
            self.editButton.addStyleName("ContentPanelEditLink")
            self.editButton.addClickListener(EventDelegate("onClick", self,
                                             self.onEditContentClick))
            ComplexPanel.insert(self, self.editButton, self.getElement(),
                                len(self.children))

        self.notifyLoadListeners()

    def onError(self, html, statusCode):
        if statusCode == 404 and self.allowEdit:
            self.editor = None
            self.originalText = ""
            DOM.setInnerHTML(self.getElement(), '')
            self.editButton = Label("create "+unescape(self.templateName))
            self.editButton.addStyleName("link")
            self.editButton.addStyleName("ContentPanelEditLink")
            self.editButton.addClickListener(EventDelegate("onClick", self,
                                             self.onEditContentClick))
            ComplexPanel.insert(self, self.editButton, self.getElement(),
                                len(self.children))
            return

        # Show the page we got in an iframe, which will hopefully show
        # the error better than we can.
        # DOM.setInnerHTML(self.getElement(), '<iframe src="'+self.getTemplatePath(self.templateName)+'"/>')

    def onTimeout(self, text):
        self.onError("Page loading timed out: "+text)

    def getElementsById(self):
        """Return a dict mapping an id to an element with that id
        inside the template; useful for post-processing."""
        return self.elementsById

    def getLinks(self):
        """Return a list of all the A HREF= elements found in the template."""
        return self.links

    def getForms(self):
        """Return a list of all the FORM elements found in the template."""
        return self.forms

    def onAttach(self):
        if not self.attached:
            SimplePanel.onAttach(self)
            if self.loaded and not self.widgetsAttached:
                self.attachWidgets()
                self.widgetsAttached = True

    def attachWidgets(self):
        """
        Attach and insert widgets into the DOM now that it has been
        loaded.  If any widgets were attached before loading, they
        will have been queued and the default implementation will
        attach them.

        Override this in subclasses to attach your own widgets after
        loading.
        """
        for attach in self.toAttach:
            self.attach(attach.name, attach.widget)
        for insert in self.toInsert:
            self.insert(insert.name, insert.widget)

    def getElementById(self, id):
        return self.elementsById[id]

    def insert(self, id, widget):
        """
        Insert a widget into the element with the given id, at the end
        of its children.
        """
        if not self.loaded:
            self.toInsert.append(PendingAttachOrInsert(id, widget))
        else:
            element = self.getElementById(id)
            if element:
                self.adopt(widget, element)
                self.children.append(widget)
            else:
                console.error("Page error: No such element " + id)
            return widget

    def attachToElement(self, element, widget):
        events = DOM.getEventsSunk(widget.getElement())
        widget.unsinkEvents(events)
        widget.setElement(element)
        widget.sinkEvents(events)
        self.adopt(widget, None)
        self.children.append(widget)

    def replaceElement(self, element, widget):
        """Replace an existing element with the given widget."""
        DOM.getParent(element).replaceChild(widget.getElement(), element)
        self.adopt(widget, None)
        self.children.append(widget)

    def attach(self, id, widget):
        """
        Attach a widget onto the element with the given id; the element
        currently associated with the widget is discarded.
        """
        if not self.loaded:
            self.toAttach.append(PendingAttachOrInsert(id, widget))
        else:
            element = self.getElementById(id)
            if element:
                self.attachToElement(element, widget)
            else:
                console.error("Page error: No such element " + id)
            return widget

    def getMeta(self, name):
        """
        Get the value of a meta-variable found in the template, or None if
        no meta tags were found with the given name.
        """
        return self.metaTags.get(name)

    def getTitle(self):
        """Return a user-friendly title for the page."""
        if self.title:
            return self.title
        else:
            return self.templateName

    def addLoadListener(self, listener):
        """
        The listener should be a function or an object implementing
        onTemplateLoaded. It will be called this TemplatePanel
        instance after the template has been loaded and after
        attachWidgets() is called.
        """
        self.loadListeners.append(listener)

    def removeLoadListener(self, listener):
        self.loadListeners.remove(listener)

    def notifyLoadListeners(self):
        for listener in self.loadListeners:
            if listener.onTemplateLoaded:
                listener.onTemplateLoaded(self)
            else:
                listener(self)

    def onEditContentClick(self, sender):
        if self.editor:
            editor = self.editor
            self.editor = None
            ComplexPanel.remove(self, editor)
            self.editButton.setText("edit " + unescape(self.templateName))
        else:
            self.editor = RichTextEditor(self.originalText)
            self.editor.addSaveListener(self)
            ComplexPanel.insert(self, self.editor, self.getElement(),
                                len(self.children))
            self.editButton.setText("close editor")

    def getTemplateSaveUrl(self, templateName):
        """
        Get the URL to post a template to when it is saved in the editor.
        """
        return self.getTemplatePath(templateName)

    def saveTemplateText(self, html):
        """
        Save the text. This method can be overridden to use a
        different save method. The default is to POST to the template
        save URL, passing a single parameter "content" with the html
        string.

        To change the target of the POST, override getTemplateSaveUrl().

        To preprocess the html, override this method in a subclass and
        perform processing there.
        """
        HTTPRequest().asyncPost(self.getTemplateSaveUrl(self.templateName),
                                "content=" + encodeURIComponent(html),
                                ContentSaveHandler(self))

    def onSave(self, sender):
        """Called when the user clicks save in the content editor."""
        html = self.editor.getHTML()
        self.saveTemplateText(html)

    def onSaveComplete(self):
        """
        Called when the template was successfully POSTed to the
        server; it reloads the template.

        Subclasses which don't use the default method of saving may
        want to call this after they successfully save the template.
        """
        self.loadTemplate(self.templateName)

