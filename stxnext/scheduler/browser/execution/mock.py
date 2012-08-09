from Products.Five import BrowserView
import simplejson as json
from random import randrange
from stxnext.scheduler.browser.execution.synchro import LOG_INFO
from time import sleep

class SynchroMockView(BrowserView):
    """ Mock for synchro system """
    
    def __call__(self, params=None):
        """ return mock response """
        response = self.mock(params)
        LOG_INFO("Mock response %s" % response)
        return response
        
    def mock(self, params):
        if params.startswith('process'):
            sleep(3)
            if randrange(2): 
                return json.dumps({"status" : "ok"})
            else:
                return json.dumps({"status" : "error"})
        elif params.startswith('status'):
            if not randrange(4):
                return json.dumps({"status" : "error", "data": ["Mock error 1", "Mock error 2"]})
            else:
                return json.dumps({"status" : "busy"})
