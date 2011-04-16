
class ChapterListLoader:
    def __init__(self, panel):
        self.panel = panel

    def onCompletion(self, text):
        res = []
        for l in text.split('\n'):
            if not l:
                continue
            l = l.split(':')
            if len(l) != 2:
                continue
            res.append([l[0].strip(), l[1].strip()])
        self.panel.setChapters(res)

    def onError(self, text, code):
        self.panel.onError(text, code)

    def onTimeout(self, text):
        self.panel.onTimeout(text)


class ChapterLoader:
    def __init__(self, panel):
        self.panel = panel

    def onCompletion(self, text):
        self.panel.setChapter(text)

    def onError(self, text, code):
        self.panel.onError(text, code)

    def onTimeout(self, text):
        self.panel.onTimeout(text)


