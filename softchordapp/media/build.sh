#!/bin/sh
# you will need to read the top level README, and run boostrap.py
# and buildout in order to make pyjsbuild

rm -fr output/

options="$*"
if [ -z $options ] ; then options="-O";fi
~/src/pyjamas-0.7/bin/pyjsbuild $options softchordapp
