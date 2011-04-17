class DF:
    def __init__(self, fmt):
        self.fmt = fmt

    def format(self, date):
        return time.strftime(self.fmt, date)

import time

def getShortDateTimeFormat():
    return DF("%d/%m/%y")

