# -*- coding: utf-8 -*-
import sys
from time import sleep
import base64
import urllib2
from datetime import datetime
import transaction
import simplejson as json
from ConfigParser import ConfigParser

from stxnext.scheduler.browser import SynchroBase
from Products.CMFCore.utils import getToolByName
from zope.component import getMultiAdapter
from stxnext.scheduler.content.properties import ISynchroProperties
from zLOG import LOG, INFO, ERROR, BLATHER
from zExceptions import Forbidden, BadRequest
from zope.component import getUtility
from zope.security import checkPermission

    
def LOG_INFO(msg, severity=INFO):
    LOG('stxnext.scheduler', severity, msg)
    
def LOG_ERROR(msg, error=None):
    if error is None:
        LOG('stxnext.scheduler', ERROR, msg)
    else:
        LOG('stxnext.scheduler', ERROR, msg, '', (error.__class__, error, sys.exc_traceback)) 

class SynchroExecute(SynchroBase):
    """ Execute pending requests """
    
    PROCESS_URL = '%(url)sprocess,%(serwis)s,%(action)s,%(timestamp)s'
    STATUS_URL =  '%(url)sstatus,%(timestamp)s'
    
    _synchro_props = None
    @property
    def synchro_props(self):
        if self._synchro_props is None:
            self._synchro_props = getUtility(ISynchroProperties)
        return self._synchro_props
    
    def olderPending(self):
        now = datetime.now()
        for entry in self.storage.pending():
            if entry.date < now:
                yield entry 
    
    def __call__(self, force=None):
        """ try executing all pending request with dates older than "now" """
        if not checkPermission('synchro.Execute', self.context):
            raise Forbidden
        if self.storage.busy:
            if force:
                LOG_INFO("Forcing synchro on busy storage")
            else:
                LOG_ERROR("Synchro is busy, use force=true to force execution")
                raise BadRequest("Synchro is busy")
        LOG_INFO("Locking synchro", BLATHER)
        self.storage.busy = True
        transaction.commit()
        LOG_INFO("Starting synchro processing", BLATHER)
        processed = 0
        try:
            for entry in self.olderPending():
                self.process(entry)
                processed += 1
            return "Synchro finished. %s entries processed" % processed
        finally:
            LOG_INFO("Unlocking synchro", BLATHER)
            self.storage.busy = False
            transaction.commit()
            LOG_INFO("Synchro finished. %s entries processed" % processed, BLATHER)
    
    def process(self, entry):
        LOG_INFO("Processing entry %s" % entry)
        entry.setCurrent()
        entry.updateTime()
        transaction.commit()
        try:
            try:
                while True:
                    response = self.executeProcess(entry)
                    status = response.get('status')
                    if status == 'ok':
                        entry.setDone()
                        LOG_INFO('Entry %s processed successfully' % entry)
                        break
                    else:
                        LOG_INFO('Processing entry: %s ended with status: %s, response: %s' % (entry, status, response))
                        response = self.executeStatus(entry)
                        status = response.get('status')
                        if status == 'ok':
                            LOG_INFO('Service ready, repeating')
                        elif status == 'busy':
                            LOG_INFO('Service busy, waiting')
                            sleep(5.0)
                            # iterate once more
                        elif status == 'error':
                            if response.get('data', None):
                                msg = ', '.join(response['data'])
                                entry.setError(msg)
                                LOG_ERROR('Entry %s ended with remote error "%s"' % (entry, msg))
                                break
                            else:
                                entry.setError('No error date received')
                                LOG_ERROR('Entry %s ended with remote error, no error data received' % (entry))
                                LOG_ERROR('Full response for entry:%s : %s' % (entry, response))
                                break
                        else:
                            entry.setError('Wrong response received')        
                            LOG_ERROR('Entry %s ended with remote error, wrong response received: %s' % (entry, response))
                            break
            
            except urllib2.HTTPError, e:
                LOG_ERROR('HTTPError %s execution: %s: %s' % (entry, e.code, e.msg), e)
                entry.setError('HTTP Error %s: %s' % (e.code, e.msg))
            except Exception, e:
                LOG_ERROR('Exception thrown during entry %s execution' % entry, e)
                entry.setError('Internal error')
        finally:
            transaction.commit()

    def execute(self, entry, url):
        """ issue HTTP request
        @return: object parsed from json
        @rtype: dict
        """
        url = url % {
            'url': self.synchro_props.url,
            'serwis' : self.synchro_props.serwis,
            'action' : entry.action,
            'timestamp' : entry.timestamp
        }
        LOG_INFO("Opening '%s'" % url)
        
        request = urllib2.Request(url) 
        if self.synchro_props.user:
            base64string = base64.encodestring('%s:%s' % (self.synchro_props.user,
                                               self.synchro_props.password))[:-1] 
            request.add_header("Authorization", "Basic %s" % base64string) 
        pipe = urllib2.urlopen(request)
        try:
            return json.load(pipe)
        finally:
            pipe.close()
            
    def execute_static_deployment(self, entry):
        """
        executes defined staticdeployment process
        @rtype: dict
        """
        response = {}
        action = entry.action
        
        def handle_error(msg):
            LOG_ERROR(msg)
            response['status'] = 'error'
            response['data'] = [msg]
            
        if not checkPermission('static.Export', self.context):
            mtool = getToolByName(self.context, 'portal_membership')
            username = mtool.getMemberInfo().get('username', '')
            errmsg = "User '%s' has no 'static.Export' permission" % username
            handle_error(errmsg)
            return response
        
        action_items = getattr(entry, 'props', {})
        staticdeployment = getMultiAdapter((self.context, self.request),
                                            name='staticdeployment-controlpanel')
        if not action_items.has_key('section_choice'):
            errmsg = "Deployment skin is not defined in config file"
            handle_error(errmsg)
            return response
        
        staticdeployment._on_save(dict(action_items))
        response['status'] = 'ok'
              
        return response

    def executeStatus(self, entry):
        """ issue the status command """
        if entry.action.startswith('static'):
            return self.execute_static_deployment(entry)
        return self.execute(entry, self.STATUS_URL)
    
    def executeProcess(self, entry):
        """ issue the process command """
        if entry.action.startswith('static'):
            return self.execute_static_deployment(entry)
        return self.execute(entry, self.PROCESS_URL)
