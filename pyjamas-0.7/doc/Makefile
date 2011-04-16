all: gendocs upload uploadexamples

gendocs:
	python gendocs.py

# you need to make this your own username,pyjamasgroupname unfortunately.
# sf being stupid.
upload:
	rsync -rlvz * lkcl,pyjamas@web.sf.net:/home/groups/p/py/pyjamas/htdocs/
	rsync -rlvz api lkcl,pyjd@web.sf.net:htdocs/

uploadexamples:
	rsync -rlvz ../examples lkcl,pyjamas@web.sf.net:/home/groups/p/py/pyjamas/htdocs/

