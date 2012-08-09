from Products.Five import BrowserView
from stxnext.scheduler.content.store import ISynchroStore

class SynchroBase(BrowserView):
    
    _storage = None
    @property
    def storage(self):
        if self._storage is None:
            self._storage = ISynchroStore(self.context)
        return self._storage
