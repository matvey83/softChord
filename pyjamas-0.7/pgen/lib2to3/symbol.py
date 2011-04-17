# Copyright 2006 Google, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

"""Export the Python grammar and symbols."""

import sys
# Local imports
from lib2to3.compiler import parse_tables

for name, symbol in parse_tables.Grammar().symbol2number.iteritems():
    setattr(sys.modules[__name__], name, symbol)

sym_name = {}
for _name, _value in globals().items():
    if type(_value) is type(0):
            sym_name[_value] = _name

