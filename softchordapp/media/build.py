#!/bin/python
import os, shutil, subprocess

MEDIA_DIR = os.path.dirname(__file__)

os.chdir(MEDIA_DIR)

# Remove the previous output dir:
out_dir = os.path.join(MEDIA_DIR, "output")
if os.path.isdir(out_dir):
    shutil.rmtree(out_dir)

#options="$*"
#if [ -z $options ] ; then options="-O";fi
#../../pyjamas-0.7/bin/pyjsbuild $options softchordapp

# Complie the app:
pyjsbuild = os.path.join("..", "..", "pyjamas-0.7", "bin", "pyjsbuild")
subprocess.call([ pyjsbuild, "softchordapp" ])


