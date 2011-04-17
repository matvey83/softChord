#
# This is an incomplete start of csv module
# The current contents should in fact go to _csp.py
#

class CSVReader(object):
    def __init__(self, lines, dialect = None, **kwargs):
        self.__values = []
        self.__inQuoted = False
        self.delimeter = kwargs.get('delimeter', ',')
        self.quotechar = kwargs.get('quotechar', '"')
        self.dialect = dialect
        self.line_num = 0

        lineno = 0
        for line in lines:
            lineno += 1
            self.addNewline(lineno)
            if line == '' or line == '\n':
                continue
            cols = line.split(self.delimeter)
            if len(cols) > 0:
                self.addValue(cols[0], True)
                for col in cols[1:]:
                    self.addValue(col, False)
        if len(self.__values) > 0:
            row = self.__values[-1]
            if len(row) > 1 and len(row[-1]) > 0:
                if row[-1][-1] == '\n':
                    row[-1] = row[-1][:-1]

    def addNewline(self, lineno):
        if self.__inQuoted:
            self.__values[-1][0] = lineno
        else:
            if len(self.__values) > 0:
                row = self.__values[-1]
                if len(row) > 1:
                    while len(row[-1]) > 0 and row[-1][-1] == '\n':
                        row[-1] = row[-1][:-1]
                    if len(row) == 2 and row[1] == '':
                        del row[1]
            self.__values.append([lineno])

    def addValue(self, value, isFirst):
        wasInQuoted = self.__inQuoted
        endOfQuoted = False
        quotechar = self.quotechar
        v = value
        # Check for end of quoted
        sv = v.rstrip()
        if len(sv) > 0 and sv[-1] == quotechar:
            svlen = len(sv)-1
            idx = svlen - 2
            while idx > 0 and sv[idx] == quotechar:
                idx -= 1
            if (svlen - idx) % 2 == 0:
                v = sv[:-1] + v[svlen+1:]
                endOfQuoted = True
        # Check for start of quoted
        if not self.__inQuoted and \
           len(v) > 0 and v[0] == quotechar:
            idx = 1
            vlen = len(v)
            while idx < vlen and v[idx] == quotechar:
                idx += 1
            if idx % 2 == 1:
                v = v[1:]
                self.__inQuoted = True
            else:
                v = value[idx:]
        if self.__inQuoted:
            v = v.replace(quotechar + quotechar, quotechar)
        if wasInQuoted:
            if isFirst:
                self.__values[-1][-1] += v
            else:
                self.__values[-1][-1] += self.delimeter + v
        else:
            self.__values[-1].append(v)
        if endOfQuoted:
            self.__inQuoted = False

    def __iter__(self):
        self.__iter = self.__values.__iter__()
        return self

    def next(self):
        v = self.__iter.next()
        self.line_num = v[0]
        return v[1:]


def reader(lines, **kwargs):
    return CSVReader(lines, **kwargs)

