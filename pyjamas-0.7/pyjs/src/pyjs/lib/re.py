
#from __pyjamas__ import debugger


# --------------------------------------------------------------------
# public interface

# flags
I = IGNORECASE = 1  # ignore case
L = LOCALE     = 2  # assume current 8-bit locale
U = UNICODE    = 4  # assume unicode locale
M = MULTILINE  = 8  # make anchors look for newline
S = DOTALL     = 16 # make dot match newline
X = VERBOSE    = 32 # ignore whitespace and comments

def match(pattern, string, flags=0):
    # Try to apply the pattern at the start of the string, returning
    # a match object, or None if no match was found.
    return compile(pattern, flags).match(string)

def search(pattern, string, flags=0):
    # Scan through string looking for a match to the pattern, returning
    # a match object, or None if no match was found.
    return compile(pattern, flags).search(string)

def sub(pattern, repl, string, count=0):
    # Return the string obtained by replacing the leftmost
    # non-overlapping occurrences of the pattern in string by the
    # replacement repl.  repl can be either a string or a callable;
    # if a callable, it's passed the match object and must return
    # a replacement string to be used.
    return compile(pattern, 0).sub(repl, string, count)

def subn(pattern, repl, string, count=0):
    # Return a 2-tuple containing (new_string, number).
    # new_string is the string obtained by replacing the leftmost
    # non-overlapping occurrences of the pattern in the source
    # string by the replacement repl.  number is the number of
    # substitutions that were made. repl can be either a string or a
    # callable; if a callable, it's passed the match object and must
    # return a replacement string to be used.
    return compile(pattern, 0).subn(repl, string, count)

def split(pattern, string, maxsplit=0):
    # Split the source string by the occurrences of the pattern,
    # returning a list containing the resulting substrings.
    return compile(pattern, 0).split(string, maxsplit)

def findall(pattern, string, flags=0):
    # Return a list of all non-overlapping matches in the string.
    #
    # If one or more groups are present in the pattern, return a
    # list of groups; this will be a list of tuples if the pattern
    # has more than one group.
    #
    # Empty matches are included in the result.
    return compile(pattern, flags).findall(string)

def finditer(pattern, string, flags=0):
    # Return an iterator over all non-overlapping matches in the
    # string.  For each match, the iterator returns a match object.
    #
    # Empty matches are included in the result.
    return compile(pattern, flags).finditer(string)

def compile(pattern, flags=0):
    return SRE_Pattern(pattern, flags, _compile(pattern, flags))

def purge():
    # "Clear the regular expression cache"
    _cache.clear()
    _cache_repl.clear()

def template(pattern, flags=0):
    # "Compile a template pattern, returning a pattern object"
    raise NotImplementedError("re.template")
    #return compile(pattern, flags|T)

_alphanum = {}
for c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890':
    _alphanum[c] = 1
del c

def escape(pattern):
    "Escape all non-alphanumeric characters in pattern."
    s = list(pattern)
    alphanum = _alphanum
    for i in range(len(pattern)):
        c = pattern[i]
        if c not in alphanum:
            if c == "\000":
                s[i] = "\\000"
            else:
                s[i] = "\\" + c
    return pattern[:0].join(s)

# --------------------------------------------------------------------
# internals

from __pyjamas__ import JS, debugger

__inline_flags_re__ = JS(r"""new RegExp("[(][?][iLmsux]+[)]")""")

_cache = {}
_cache_repl = {}
_MAXCACHE = 100

def _compile(pat, flags=0):
    from __pyjamas__ import JS
    cachekey = (pat, flags)
    p = _cache.get(cachekey)
    if p is not None:
        return p

    flgs = ""
    while True:
        m = __inline_flags_re__.Exec(pat)
        if m is None:
            break
        pat = pat.__replace(__inline_flags_re__, "")
        for m in list(m):
            for c in m:
                if c in ['(','?',')']:
                    pass
                elif c == 'i':
                    flags |= IGNORECASE
                elif c == 'L':
                    flags |= LOCALE
                elif c == 'm':
                    flags |= MULTILINE
                elif c == 's':
                    flags |= DOTALL
                elif c == 'u':
                    flags |= UNICODE
                elif c == 'x':
                    flags |= VERBOSE

    if flags:
        if flags & LOCALE:
            raise NotImplementedError("L/LOCALE flag is not implemented")
        if flags & UNICODE:
            raise NotImplementedError("U/UNICODE flag is not implemented")
        if flags & VERBOSE:
            raise NotImplementedError("X/VERBOSE flag is not implemented")
        if flags & DOTALL:
            # Replace the '.' with '[\s\S]' iff the dot is not within []
            p = ''
            brack = -1
            backslash = -2
            for i, c in enumerate(pat):
                if backslash != i - 1:
                    if brack < 0:
                        if c == '[':
                            brack = i
                        elif c == '.':
                            c = r'[\s\S]'
                        elif c == '\\':
                            backslash = i
                    else:
                        if c == ']' and brack != i-1:
                            brack = -1
                p += c
            pat = p
        if flags & IGNORECASE:
            flgs += 'i'
        if flags & MULTILINE:
            flgs += 'm'
    spat = r"([\s\S]*?)(" + pat + r")[\s\S]*"
    p = JS(r"""new RegExp(pat, flgs)"""), JS(r"""new RegExp(spat, flgs)"""), JS(r"""new RegExp(pat, "g"+flgs)""")
    if len(_cache) >= _MAXCACHE:
        _cache.clear()
    _cache[cachekey] = p
    return p

class SRE_Match:
    def __init__(self, re, string, pos, endpos, groups, start, lastindex, lastgroup):
        self._groups = groups
        self._start = start
        self._end   = start + len(groups[0])
        self.re = re
        self.string = string
        self.pos = pos
        self.endpos = endpos
        self.lastindex = lastindex
        self.lastgroup = lastgroup

    def start(self, group=0):
        # Returns the indices of the start of the substring matched by group;
        # group defaults to zero (meaning the whole matched substring). Returns -1
        # if group exists but did not contribute to the match.
        if group != 0:
            raise NotImplementedError("group argument not supported")
        return self._start

    def end(self, group=0):
        # Returns the indices of the end of the substring matched by group;
        # group defaults to zero (meaning the whole matched substring). Returns -1
        # if group exists but did not contribute to the match.
        if group != 0:
            raise NotImplementedError("group argument not supported")
        return self._end

    def span(self, group=0):
        # Returns the 2-tuple (m.start(group), m.end(group)).
        if group != 0:
            raise NotImplementedError("group argument not supported")
        return self.start(group), self.end(group)

    def expand(self, template):
        # Return the string obtained by doing backslash substitution and
        # resolving group references on template.
        raise NotImplementedError('expand')

    def groups(self, default=None):
        # Returns a tuple containing all the subgroups of the match. The
        # default argument is used for groups that did not participate in the
        # match (defaults to None).
        return tuple(self._groups[1:])

    def groupdict(self, default=None):
        # Return a dictionary containing all the named subgroups of the match.
        # The default argument is used for groups that did not participate in the
        # match (defaults to None).
        raise NotImplementedError('groupdict')

    def group(self, *args):
        # Returns one or more subgroups of the match. Each argument is either a
        # group index or a group name.
        if len(args) == 0:
            args = (0,)
        grouplist = []
        for group in args:
            grouplist.append(self._groups[group])
        if len(grouplist) == 1:
            return grouplist[0]
        else:
            return tuple(grouplist)

    def __copy__():
        raise TypeError, "cannot copy this pattern object"

    def __deepcopy__():
        raise TypeError, "cannot copy this pattern object"


class SRE_Pattern:
    def __init__(self, pat, flags, code):
        self.pat = pat
        self.flags = flags
        self.match_code = code[0]
        self.search_code = code[1]
        self.findall_code = code[2]
        self.groups = groups
        self.groupindex = groupindex # Maps group names to group indices
        self._indexgroup = indexgroup # Maps indices to group names

    def match(self, string, pos=0, endpos=None):
        # If zero or more characters at the beginning of string match this
        # regular expression, return a corresponding MatchObject instance. Return
        # None if the string does not match the pattern.
        if not endpos is None:
            string = string[:endpos]
        else:
            endpos = len(string)
        if pos == 0:
            groups = self.match_code.Exec(string)
            if groups is None:
                return None
            groups = list(groups)
        elif pos >= len(string):
            return None
        else:
            # Strickly, we shouldn't use string[pos:]
            # The '^' pattern character should match at the real beginning of 
            # the string and at positions just after a newline, but not 
            # necessarily at the index where the search is to start.
            # Maybe, we should raise an error if there's a '^' in pat (not in [])
            groups = self.match_code.Exec(string[pos:])
            if groups is None:
                return None
            if groups.index != 0:
                return None
            groups = list(groups)
        return SRE_Match(self, string, pos, endpos, groups, pos, None, None)

    def search(self, string, pos=0, endpos=None):
        # Scan through string looking for a location where this regular
        # expression produces a match, and return a corresponding MatchObject
        # instance. Return None if no position in the string matches the
        # pattern.
        if not endpos is None:
            string = string[:endpos]
        if pos == 0:
            groups = self.search_code.Exec(string)
            if groups is None:
                return None
            groups = list(groups)
        elif pos >= len(string):
            return None
        else:
            # Strickly, we shouldn't use string[pos:]
            groups = self.search_code.Exec(string[pos:])
            if groups is None:
                return None
            groups = list(groups)
        return SRE_Match(self, string, pos, endpos, groups[2:], pos + len(groups[1]),None, None)

    def findall(self, string, pos=0, endpos=None):
        # Return a list of all non-overlapping matches of pattern in string.
        if not endpos is None:
            string = string[:endpos]
        all = []
        while True:
            m = self.search(string, pos)
            if m is None:
                break
            span = m.span()
            all.append(string[span[0]:span[1]])
            pos = span[1]
        return all
        # Next line bugs in FF2
        return list(string[pos:].match(self.findall_code))

    def sub(self, repl, string, count=0):
        # Return the string obtained by replacing the leftmost non-overlapping
        # occurrences of pattern in string by the replacement repl.
        return self.subn(repl, string, count)[0]

    def subn(self, repl, string, count=0):
        # Return the tuple (new_string, number_of_subs_made) found by replacing
        # the leftmost non-overlapping occurrences of pattern with the replacement
        # repl.
        res = ''
        n = 0
        subst = repl
        pos = 0
        while count >= 0:
            m = self.search(string, pos)
            if m is None:
                break
            span = m.span()
            if callable(repl):
                subst = repl(m)
            res += string[pos:span[0]]
            res += subst
            pos = span[1]
            n += 1
            if count:
                if count == 1:
                    break
                count -= 1
        return res + string[pos:], n

    def split(self, string, maxsplit=0):
        # Split string by the occurrences of pattern.
        splitted = []
        pos = 0
        while maxsplit >= 0:
            m = self.search(string, pos)
            if m is None:
                break
            span = m.span()
            splitted.append(string[pos:span[0]])
            pos = span[1]
        if pos < len(string):
            splitted.append(string[pos:])
        return splitted

    def finditer(self, string, pos=0, endpos=None):
        # Return a list of all non-overlapping matches of pattern in string.
        return self.findall(string, pos, endpos).__iter__()

    def scanner(self, string, start=0, end=None):
        raise NotImplementedError('scanner')

    def __copy__(self):
        raise TypeError, "cannot copy this pattern object"

    def __deepcopy__(self):
        raise TypeError, "cannot copy this pattern object"



