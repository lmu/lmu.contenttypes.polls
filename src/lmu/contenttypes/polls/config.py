# -*- coding: utf-8 -*-

from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
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

POLL_TYPES = SimpleVocabulary([
    SimpleTerm(value=u'poll_star', title=_(u'Star Poll')),
    SimpleTerm(value=u'poll_true_not_true', title=_(u'Agree / Disagree Poll')),
    SimpleTerm(value=u'poll_like_dislike', title=_(u'Like / Dislike Poll')),
    SimpleTerm(value=u'poll_free', title=_(u'Free Poll')),
])

SHOW_RESULTS_OPTIONS = SimpleVocabulary([
    SimpleTerm(value=u'after_vote', title=_(u'Show after Vote')),
    SimpleTerm(value=u'with_vote', title=_(u'Show directly with Vote question')),  # NOQA
    SimpleTerm(value=u'never', title=_(u'Never Show result for user')),
])

STAR_POLL_RESULT_GRAPH_OPTIONS = SimpleVocabulary([
    SimpleTerm(value=u'average_bar', title=_(u'Average + Bar Chart')),
    SimpleTerm(value=u'bar', title=_(u'Bar Chart')),
    SimpleTerm(value=u'average', title=_(u'Average Chart')),
    SimpleTerm(value=u'numbers', title=_(u'Numbers Only'))
])

GENERAL_RESULT_GRAPH_OPTIONS = SimpleVocabulary([
    SimpleTerm(value=u'bar', title=_(u'Bar Chart')),
    SimpleTerm(value=u'pie', title=_(u'Pie Chart')),
    SimpleTerm(value=u'numbers', title=_(u'Numbers Only'))
])


class ResultViewOptionsVocabulary(object):
    """Vocabulary factory returning available languages for the portal.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        return SHOW_RESULTS_OPTIONS

ResultViewOptionsVocabularyFactory = ResultViewOptionsVocabulary()


class StarPollResultGraphOptionsVocabulary(object):
    """Vocabulary factory returning available languages for the portal.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        return STAR_POLL_RESULT_GRAPH_OPTIONS

StarPollResultGraphOptionsVocabularyFactory = StarPollResultGraphOptionsVocabulary()


class TwoOptionResultGraphOptionsVocabulary(object):
    """Vocabulary factory returning available languages for the portal.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        return GENERAL_RESULT_GRAPH_OPTIONS

TwoOptionResultGraphOptionsVocabularyFactory = TwoOptionResultGraphOptionsVocabulary()
