from zope.interface import Interface, implements, Attribute
from persistent import Persistent
from persistent.dict import PersistentDict
from zope.annotation.interfaces import IAnnotations
from BTrees.OOBTree import OOBTree 
from datetime import datetime
import random
from time import time
from Products.Five import BrowserView

ANNOTATION_KEY = 'stxnext.scheduler.store'

def date_to_id(date):
    return '%s_%s' % (date.strftime('%Y_%m_%d_%H_%M_%S'), random.randrange(10000))

class SYNCHRO_STATUS(object):
    PENDING = 0
    CURRENT = 1
    DONE = 2
    ERROR = 3

class ISynchroEntry(Interface):
    
    date = Attribute("(tz-naive) datetime.datetime object")
    creation_date = Attribute("creation date")
    status = Attribute("status, one of PENDING, CURRENT, DONE, ERROR")
    execution_date = Attribute("date of last execution attempt")
    action = Attribute("action that should be performed")
    error = Attribute("error description or None")
    timestamp = Attribute("unix timestamp")
    
    def setPending(self):
        """ set state to PENDING """
        
    def setCurrent(self):
        """ set state to CURRENT """
    
    def setDone(self):
        """ set state do DONE """
    
    def setError(self, msg):
        """ set state to ERROR, save error message """
        
    def updateTime(self):
        """ generate new timestamp """
        
class set_status(object):
    """ method decorator """
    def __init__(self, status):
        self.status = status
        
    def __call__(self, func):
        def inner(this):
            this.status = self.status
        inner.__name__ = func.__name__
        return inner
    
class SynchroEntry(Persistent):
    
    implements(ISynchroEntry)
    
    def __init__(self, date, action, props={}):
        self.date = date
        self.setPending()
        self.creation_date = datetime.now()
        self.action = action
        self.id = date_to_id(self.creation_date)
        self.error = None
        self.timestamp = None
        self.props = props
        
    @set_status(SYNCHRO_STATUS.PENDING)
    def setPending(self): pass
    
    @set_status(SYNCHRO_STATUS.CURRENT)
    def setCurrent(self): pass
    
    @set_status(SYNCHRO_STATUS.DONE)
    def setDone(self): pass
    
    def setError(self, msg):
        self.status = SYNCHRO_STATUS.ERROR
        self.error = msg
        
    def updateTime(self):
        self.timestamp = int(time() * 1000.0)
        
    def __str__(self):
        return '<Synchro "%s"@%s created %s>' % (self.action, self.date, self.creation_date)    

class ISynchroStore(Interface):
    """ Interface for synchro entries storage """
    
    def __iter__(self):
        """ iterate over all entries """
        
    def pending(self):
        """ iterate over pending entries """
        
    def current(self):
        """ iterate over current entries """
        
    def done(self):
        """ iterate over done entries """
        
    def error(self):
        """ iterate over failed entries """
        
    def add(self, date, action):
        """ add new entry to the store and return it
        @rtype: ISynchroEntry
        """
        
    def get(self, id):
        """ return stored entry with given id
        @rtype: ISynchroEntry
        """
        
    def remove(self, id):
        """ remove stored entry with given id """
        
    busy = Attribute("True if synchro is in progress")

class iteration_with_status(object):
    """ method decorator """
    def __init__(self, status):
        self.status = status
        
    def __call__(self, func):
        def inner(this):
            for entry in this:
                if entry.status == self.status:
                    yield entry
        inner.__name__ = func.__name__
        return inner
    
class SynchroStore(Persistent):
    """ Synchro entries storage """
    
    implements(ISynchroStore)

    def __init__(self):
        self._entries = OOBTree()
        self.busy = False
        
    def __iter__(self):
        for entry in self._entries.itervalues():
            yield entry
        
    def add(self, date, action, props={}):
        entry = SynchroEntry(date, action, props)
        self._entries[entry.id] = entry
    
    def remove(self, id):
        del self._entries[id]
    
    def get(self, id):
        return self._entries[id]
        
    @iteration_with_status(SYNCHRO_STATUS.PENDING)
    def pending(self): pass
    
    @iteration_with_status(SYNCHRO_STATUS.CURRENT)
    def current(self): pass
    
    @iteration_with_status(SYNCHRO_STATUS.DONE)
    def done(self): pass
    
    @iteration_with_status(SYNCHRO_STATUS.ERROR)
    def error(self): pass
        
def SynchroAdapter(site):
    """ returns SynchroStore of site """
    annotations = IAnnotations(site)
    if not annotations.has_key(ANNOTATION_KEY):
        annotations[ANNOTATION_KEY] = SynchroStore()
    return annotations[ANNOTATION_KEY]

class SynchroClear(BrowserView):
    """ removes synchro store from annotations """
    
    def __call__(self):
        """ """
        annotations = IAnnotations(self.context)
        if annotations.has_key(ANNOTATION_KEY):
            del annotations[ANNOTATION_KEY]
            return "CLEARED"
        else:
            return "NOTHING TO CLEAR"
