
function pyjs_createHttpRequest(){

	if(window.ActiveXObject){
		try {
			return new ActiveXObject("Msxml2.XMLHTTP");
		} catch (e) {
			try {
				return new ActiveXObject("Microsoft.XMLHTTP");
			} catch (e2) {
				return null;
	 		}
	 	}
	} else if(window.XMLHttpRequest){
		return new XMLHttpRequest();
	} else {
		return null;
	}
}

/**
 * activate_css(str)
 *
 * looks for any < link > in the input and sets up a corresponding link node
 * in the main document.
 *
 */

function pyjs_activate_css(targetnode)
{
	var scriptnodes = targetnode.getElementsByTagName('link')
	var LC;
	for (LC = 0; LC < scriptnodes.length; LC++)
	{
		var sn = scriptnodes[LC];
		sn.parentNode.removeChild(sn);

		fileref = document.createElement('link')

		if (sn.href)
		{
			fileref.href = sn.href;
		}
		else
		{
			fileref.text = sn.text;
		}

		fileref.rel = "stylesheet";
		fileref.type = "text/css";

		document.getElementsByTagName("head").item(0).appendChild(fileref);
	}
}

/**
 * activate_javascript(str)
 *
 * looks for any < script > in the input text and sets up a corresponding
 * script node in the main document.
 *
 */

function pyjs_activate_javascript(txt)
{
    var fileref = document.createElement('script')

    /*alert(txt);*/

    fileref.text = txt;
    fileref.type = "text/javascript";
    fileref.language = "javascript";
    /*
    fileref.defer = true;
    */

    /*alert(fileref.text);*/

    /*
    var debug = document.createElement('pre');
    debug.innerHTML = 'test';
    debug.innerHTML += "href:" + sn.src + " text:" + fileref.text;
    var bodyels = document.getElementsByTagName("body");
    bodyels[bodyels.length-1].appendChild(debug);
    */

    fileref = fileref.cloneNode(true);


    document.getElementsByTagName("head").item(0).appendChild(fileref);
}

function pyjs_eval(str)
{
    if (window.execScript) {
        return window.execScript(str);
    } else {
        return eval(str);
    }
}

/**
 * ajax_eval(url)
 *
 * @param url	load and activate url
 * @returns		readyState
 */

function pyjs_ajax_eval(url, on_load_fn, async)
{
    window.status = ('Loading ' + url);
    alert('Loading ' + url + async);

	var xhtoj = pyjs_createHttpRequest()
	var res = xhtoj.open("GET", url , async );

	xhtoj.onreadystatechange = function() 
	{
		if ((xhtoj.readyState==4) && (xhtoj.status == 200) )
		{
			str = xhtoj.responseText;

            pyjs_activate_javascript(str);

            window.status = ('Loaded ' + url);

            if (on_load_fn)
                pyjs_eval(on_load_fn);
		}
	}

	xhtoj.send("")
}

/**
 * pyjs_load_script
 *
 * @param url      load script url
 * @param module   module name
 * @param onload   text of function to be eval/executed on successful load
 */

function pyjs_load_script(url, onload, async)
{
    window.status = ('Loading ' + url);

    var e = document.createElement("script");
    e.src = url;
    e.type="text/javascript";
    e.language = "javascript";
    e.defer = async;
    e.onload = function()
    {
        window.status = ('Loaded ' + url);
        if (onload)
            pyjs_eval(onload);
        return true;
    };
    document.getElementsByTagName("head")[0].appendChild(e);
}

/**
 * ajax_dlink_refresh(oj,url)
 *
 * @param id	id of element for insert
 * @param url	load url
 * @param timeout	refresh timeout period, ms
 * @returns		readyState
 */

/* use these to overrun an existing timeout, so that
   we don't end up with several of them!
 */
var running_timeout = 0;
var timeout_idname;
var timeout_url;
var timeout_on_load_fn;
var redo_timeout;
var timeout_id = null;

function pyjs_ajax_dlink_refresh(idname, url, on_load_fn, timeout)
{
	timeout_idname = idname;
	timeout_url = url;
	timeout_on_load_fn = on_load_fn;
	redo_timeout = timeout;
	if (running_timeout)
		return;
	timeout_id = setTimeout("pyjs_do_ajax_dlink_refresh()", timeout);
	running_timeout = 1;
}

function pyjs_do_ajax_dlink_refresh()
{
	if (pyjs_ajax_dlink(timeout_idname, timeout_url, timeout_on_load_fn) == 0)
	{
        timeout_id = null;
		running_timeout = 0;
		return;
	}
    timeout_id = null;
	running_timeout = 0;
	ajax_dlink_refresh(timeout_idname, timeout_url, timeout_on_load_fn,
                       redo_timeout);
}

/**
 * ajax_dlink(oj,url)
 *
 * @param id	id of element for insert
 * @param url	load url
 * @returns		readyState
 */

function pyjs_ajax_dlink(idname, url, on_load_fn)
{
	var body = document.body;

    if (timeout_id)
        clearTimeout(timeout_id); /* really important - get into a mess otherwise */
	var xhtoj = pyjs_createHttpRequest();

	xhtoj.onreadystatechange = function() 
	{
		if (xhtoj.readyState==4)
		{
			var jsnode = 0;
			if (xhtoj.status == 200)
			{
				txt = xhtoj.responseText;

				jsnode = null;

                if (idname)
                    jsnode = document.getElementById(idname);

				if (!jsnode)
				{
                    jsnode = document.createElement('script')
                }

                /*
                var tst = document.createElement('html')
                tst.innerHTML = str;
                */
                pyjs_activate_javascript(txt);
                if (on_load_fn)
                {
                    alert(on_load_fn);
                    /*if (window.execScript) {
                        window.execScript(on_load_fn);
                    } else {
                        eval(on_load_fn);
                    }
                    */
                    test_fn();
                }

                return 1;
			}
			else
			{
				jsnode = document.getElementById(idname);

				if (jsnode)
				{
					jsnode.innerHTML = xhtoj.status;
				}
			}
		}
	}

	xhtoj.open("GET", url , true );
	xhtoj.send("");

	return 0;
}


