# -*- coding: utf-8 -*-
import logging

from Products.CMFPlone.interfaces import INonInstallable
from plone import api
from zope.interface import implements

from lmu.contenttypes.polls.config import PROJECTNAME
from lmu.contenttypes.polls.interfaces import IHiddenProfiles

logger = logging.getLogger(PROJECTNAME)


class HiddenProfiles(object):
    implements(INonInstallable, IHiddenProfiles)

    def getNonInstallableProfiles(self):
        profiles = ['lmu.contenttypes.polls:uninstall', ]
        return profiles


def updateWorkflowDefinitions(portal):
    wf_tool = api.portal.get_tool(name='portal_workflow')
    wf_tool.updateRoleMappings()
    logger.info(u'Workflow definitions updated')


def setupVarious(context):
    if context.readDataFile('lmu.contenttypes.polls.marker.txt') is None:
        # not your add-on
        return

    portal = context.getSite()
    updateWorkflowDefinitions(portal)
