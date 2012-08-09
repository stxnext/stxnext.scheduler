# -*- coding: utf-8 -*-
import os.path
from ConfigParser import ConfigParser

from zope.interface import Interface, implements, Attribute
from Products.CMFCore.utils import getToolByName

def get_config_path():
    """
    """
    config_path = os.path.join(CLIENT_HOME, '..', '..', 'etc', 'synchro.ini')
    if not os.path.isfile(config_path):
        config_path = os.path.join(os.path.dirname(__file__), '..', 'etc', 'synchro.ini')
    return config_path

class ISynchroProperties(Interface):
    """ properties defined in portal_properties """
    
    url = Attribute("URL to synchro application")
    serwis = Attribute("serwis to use with synchro application")
    actions = Attribute("possible actions (iterable of two-element tuples (id, Title))")
    user = Attribute("username")
    password = Attribute("password")
    
    sections = Attribute("sections")

class SynchroProperties(object):
    """ properties wrapper """
    
    implements(ISynchroProperties)
    
    def __init__(self):
        config_path = os.path.normpath(get_config_path())
        config_file = open(config_path, 'r')
        try:
            config = ConfigParser() 
            config.readfp(config_file)
            
            self.url = config.get('config', 'url')
            self.serwis = config.get('config', 'serwis')
            self.user = config.get('config', 'user')
            self.password = config.get('config', 'password').decode('rot13').encode('utf-8')
            self.actions = config.items('actions')
            
            self.sections = config.sections()
            for section in self.sections:
                setattr(self, section, config.items(section))
            
        finally:
            config_file.close()
