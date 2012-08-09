# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from exceptions import LookupError
from DateTime import DateTime

from zExceptions import Forbidden
from zope.component import getMultiAdapter, getUtility
from zope.interface import Interface, implements, alsoProvides
from zope.formlib.form import Fields, FormFields, action, applyChanges, Field
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.schema.interfaces import IVocabularyFactory
from zope.component import getUtility
from zope.security import checkPermission
from zope.schema import Datetime, ValidationError, Choice

from plone.app.controlpanel.form import ControlPanelForm
from Products.CMFCore.utils import getToolByName
from Products.CMFDefault.formlib.schema import ProxyFieldProperty, SchemaAdapterBase
from Products.CMFPlone import PloneMessageFactory as _
from plone.app.form.validators import null_validator
from Products.statusmessages.interfaces import IStatusMessage
from plone.protect import CheckAuthenticator
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.app.controlpanel.interfaces import IPloneControlPanelForm
from stxnext.scheduler.browser import SynchroBase
from stxnext.scheduler.content.properties import ISynchroProperties

class DateInThePast(ValidationError):
    "Date is in the past"

def validate_date(value):
    now = datetime.now()
    if value.date() < now.date():
        raise DateInThePast(value)
    if value.date() == now.date() and value.time() < (now - timedelta(minutes = 5)).time():
        raise DateInThePast(value)
    return True

class ISynchroForm(IPloneControlPanelForm):
    """ Synchro control-panel form """

    def getRequests(self):
        """ return iterable of already issued requests """

class ISynchro(Interface):
    """
    Synchro manage form.
    """
    date = Datetime(
        title=_('Data zakolejkowania'),
        required=True,
        description=_(u'Data zakolejkowania akcji podana w formacie RRRR/MM/DD GG:MM:SS'),
        constraint=validate_date
        )
    
    synchro_action = Choice(
        title=_(u'Akcja'),
        description=_(u'Akcja do zakolejkowania'),
        required=True,
        vocabulary='stxnext.scheduler.vocabularies.Actions'
        )

class SynchroAdapter(SchemaAdapterBase):
    """
    Storages for particular form fields.
    """
    #date = ProxyFieldProperty(ISynchro['date'])
    synchro_action = ProxyFieldProperty(ISynchro['synchro_action'])
    
    def __init__(self, context):
        super(SynchroAdapter, self).__init__(context)
        self.date = unicode(DateTime().strftime('%Y/%m/%d %H:%M:%S'))
        
    def todayNight(self):
        """ return 'almost' midnight datetime """
        now = datetime.now()
        return now.replace(hour=23, minute=59, second=59, microsecond=0)

class SynchroForm(ControlPanelForm, SynchroBase):
    """
    Synchro form.
    """
    implements(ISynchroForm)
    template = ViewPageTemplateFile('synchro-panel.pt')
    label = _('Synchro')
    description = _(u'')
    form_name = _(u'Panel kolejkowania synchronizacji')
    form_fields = FormFields(ISynchro)
    
    def __init__(self, *args, **kwargs):
        super(SynchroForm, self).__init__(*args, **kwargs)
        vocab_factory = getUtility(IVocabularyFactory, name='stxnext.scheduler.vocabularies.Actions')
        self.vocabulary = vocab_factory(self.context)
        
    def getVocabValue(self, val):
        """ """
        try:
            return self.vocabulary.getTerm(val).token
        except:
            return val
    
    def getPendingEntries(self):
        """ """
        pending = [i for i in self.storage.pending()]
        pending.reverse()
        return pending
    
    def getCurrentEntries(self):
        """ """
        current = [i for i in self.storage.current()]
        current.reverse()
        return current
    
    def getDoneEntries(self):
        """ """
        done = [i for i in self.storage.done()]
        done.reverse()
        return done
    
    def getErrorEntries(self):
        """ """
        error = [i for i in self.storage.error()]
        error.reverse()
        return error
    
    def isBusy(self):
        """ """
        return self.storage.busy
   
    @action(_(u'label_save', default=u'Save'), name=u'save')
    def handle_edit_action(self, action, data):
        CheckAuthenticator(self.request)
        date = data['date'].replace(tzinfo=None)
        action = data['synchro_action']
        self.store(date, action)
        messages = IStatusMessage(self.request)
        messages.addStatusMessage(_("Akcja zakolejkowana."), type="info")
        url = getMultiAdapter((self.context, self.request), name='absolute_url')()
        return self.request.response.redirect(url + '/@@synchro-controlpanel')

    @action(_(u'label_cancel', default=u'Cancel'), validator=null_validator, name=u'cancel')
    def handle_cancel_action(self, action, data):
        messages = IStatusMessage(self.request)
        messages.addStatusMessage(_("Zmiany anulowano."), type="info")
        url = getMultiAdapter((self.context, self.request), name='absolute_url')()
        return self.request.response.redirect(url + '/plone_control_panel')
    
    def store(self, date, action):
        return self.storage.add(date, action)
    
class SynchroRemove(SynchroBase):
    
    def __call__(self, id=None):
        """ """
        if not checkPermission('synchro.Execute', self.context):
            raise Forbidden
        self.storage.remove(id)
        messages = IStatusMessage(self.request)
        messages.addStatusMessage(_("Entry removed"), type="info")
        url = getMultiAdapter((self.context, self.request), name='absolute_url')()
        return self.request.response.redirect(url + '/@@synchro-controlpanel')

class SynchroRepeat(SynchroBase):
        
    def __call__(self, id=None):
        """ """
        if not checkPermission('synchro.Execute', self.context):
            raise Forbidden
        entry = self.storage.get(id)
        entry.setPending()
        messages = IStatusMessage(self.request)
        messages.addStatusMessage(_("Status changed to PENDING"), type="info")
        url = getMultiAdapter((self.context, self.request), name='absolute_url')()
        return self.request.response.redirect(url + '/@@synchro-controlpanel')


def SynchroActionsVocabularyFactory(context):
    props = getUtility(ISynchroProperties)
    actions = []
    for action_id, action_title in props.actions:
        actions.append(SimpleTerm(action_id, action_title))
    return SimpleVocabulary(actions)
alsoProvides(SynchroActionsVocabularyFactory, IVocabularyFactory)
