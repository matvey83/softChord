from zope.testing.doctestunit import DocFileSuite
import doctest
import unittest

def test_suite():
    translator = DocFileSuite('translator.txt',
                optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
                        )
    browser = DocFileSuite('browser.txt',
                optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
                        )
    sm = DocFileSuite('sm.txt',
                optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
                      )
    util = DocFileSuite('util.txt',
                optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
                        )
    s = unittest.TestSuite((translator, browser, sm, util))
    return s
