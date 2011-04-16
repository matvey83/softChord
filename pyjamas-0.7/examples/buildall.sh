#!/bin/sh
options="$@"

if echo $options |grep -- '--downloads-yes'>/dev/null ; then
	DOWNLOADS=yes
	export DOWNLOADS
	options=`echo "$options"|sed 's/--downloads-yes//g'`
fi
if echo $options |grep -- '--downloads-no'>/dev/null ; then
	DOWNLOADS=no
	export DOWNLOADS
	options=`echo "$options"|sed 's/--downloads-no//g'`
fi

(cd asteroids; ./build.sh $options)
(cd browserdetect; ./build.sh $options)
(cd dynamictable; ./build.sh $options)
(cd gears; ./build.sh $options)
(cd gridtest; ./build.sh $options)
(cd helloworld; ./build.sh $options)
(cd jsonrpc; ./build.sh $options)
(cd kitchensink; ./build.sh $options)
(cd libtest; ./build.sh $options)
(cd mail; ./build.sh $options)
(cd onclicktest; ./build.sh $options)
(cd maparea; ./build.sh $options)
(cd addonsgallery; ./build.sh $options)
(cd controls; ./build.sh $options)
(cd formpanel; ./build.sh $options)
(cd getattr; ./build.sh $options)
(cd gridedit; ./build.sh $options)
(cd infohierarchy; ./build.sh $options)
(cd jsobject; ./build.sh $options)
(cd jsimport; ./build.sh $options)
(cd showcase; python compile.py $options)
(cd slideshow; ./build.sh $options)
(cd splitpanel; ./build.sh $options)
(cd tabpanelwidget; ./build.sh $options)
(cd toggle; ./build.sh $options)
(cd widgets; ./build.sh $options)
(cd ajaxlibtest; ./build.sh $options)
(cd xmldoc; ./build.sh $options)
(cd lightout; ./build.sh $options)
(cd employeeadmin; ./build.sh $options)
(cd timesheet; ./build.sh $options)
(cd datefield; ./build.sh $options)
(cd svgtest; ./build.sh $options)
(cd canvasprocessing; ./build.sh $options)
(cd toggle; ./build.sh $options)
(cd gcharttestapp; ./build.sh $options)
(cd gwtcanvas; ./build.sh $options)

