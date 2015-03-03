# -*- coding: utf-8 -*-

from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

from lmu.contenttypes.polls import MessageFactory as _

PROJECTNAME = 'lmu.contenttypes.polls'
COOKIE_KEY = 'lmu.contenttypes.polls.%s'
MEMBERS_ANNO_KEY = 'voters_members_id'
VOTE_ANNO_KEY = 'option.%02d'

ALL_ROLES = ['Anonymous',
             'Contributor',
             'Editor',
             'Manager',
             'Member',
             'Reader',
             'Reviewer',
             'Site Administrator']

PERMISSION_VOTE = 'lmu.contenttypes.polls: Vote'

graph_options = SimpleVocabulary(
    [SimpleTerm(value=u'bar', title=_(u'Bar Chart')),
     SimpleTerm(value=u'pie', title=_(u'Pie Chart')),
     SimpleTerm(value=u'numbers', title=_(u'Numbers Only'))])
