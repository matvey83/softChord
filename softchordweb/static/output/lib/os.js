/* start module: os */
var os;
$pyjs.loaded_modules['os'] = function (__mod_name__) {
	if($pyjs.loaded_modules['os'].__was_initialized__) return $pyjs.loaded_modules['os'];
	os = $pyjs.loaded_modules["os"];
	os.__was_initialized__ = true;
	if ((__mod_name__ === null) || (typeof __mod_name__ == 'undefined')) __mod_name__ = 'os';
	var __name__ = os.__name__ = __mod_name__;


	os['urandom'] = function(n) {

		throw (pyjslib['NotImplementedError'](String('/dev/urandom (or equivalent) not found')));
		return os.bs;
	};
	os['urandom'].__name__ = 'urandom';

	os['urandom'].__bind_type__ = 0;
	os['urandom'].__args__ = [null,null,['n']];
	return this;
}; /* end os */


/* end module: os */


