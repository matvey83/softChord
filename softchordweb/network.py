# -*- coding: utf-8 -*-

import simplejson
import sys

#### JSONRPC ####

def HttpResponse(content):
    return content

class JSONRPCService: # original code from : http://trac.pyworks.org/pyjamas/wiki/DjangoWithPyJamas
	def __init__(self, method_map={}):
		self.method_map = method_map
	
	def add_method(self, name, method):
		self.method_map[name] = method
		
	def __call__(self, request, extra=None):
		#assert extra == None # we do not yet support GET requests, something pyjamas do not use anyways.
		data = simplejson.loads(request)
		id, method, params = data["id"], data["method"], [request,] + data["params"] # altered to "forward" the request parameter when a member method is invocated <julien@pimentech.net>
		if method in self.method_map:
			result = self.method_map[method](*params)
			return HttpResponse(simplejson.dumps({'id': id, 'result': result}))
		else:
			return HttpResponse(simplejson.dumps({'id': id, 'error': "No such method", 'code': -1}))


# decorators support available from Python 2.4
if sys.version_info[0] > 2 or (sys.version_info[0] == 2 and sys.version_info[1] >= 4):
	def jsonremote(service):
		"""
		makes JSONRPCService a decorator so that you can write :
		
		from django.pimentech.network import *

		chatservice = JSONRPCService()

		@jsonremote(chatservice, 'login')
		def login(request, user_name):
			(...)
		
		"""
		
		def remotify(func):
			if isinstance(service, JSONRPCService):
				service.add_method(func.__name__, func)
			else:
				raise NotImplementedError, 'Service "%s" not found' % str(service.__name__)
			return func

		return remotify
		
