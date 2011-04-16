#!/bin/sh
# you will need to read the top level README, and run boostrap.py
# and buildout in order to make pyjsbuild

options="$@"
../../bin/pyjsbuild --print-statements $options CanvasProcessing
