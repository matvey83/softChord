VERSION=0.7

help:
	@echo
	@echo choose one of the following:
	@echo "    make local-build"
	@echo "    make system-install"
	@echo

# 'sandbox' build - can be used locally.
# e.g. building examples with ../../bin/pyjsbuild
local-build:
	python bootstrap.py

# must be done as root, duh.
system-install:
	python bootstrap.py /usr/share/pyjamas /usr
	python run_bootstrap_first_then_setup.py install

distclean:
	rm -rf bin build
	rm -f pyjd/__init__.py
