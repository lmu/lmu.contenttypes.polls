# -*- coding: utf-8 -*-

from collective.z3cform.widgets.enhancedtextlines import EnhancedTextLinesFieldWidget
from plone import api
from plone.directives import form
from zope import schema
from zope.component import queryUtility
from zope.interface import alsoProvides
from zope.interface import Interface
from zope.interface import Invalid
from zope.interface import invariant
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

from lmu.contenttypes.polls import config
from lmu.contenttypes.polls import MessageFactory as _


class IHiddenProfiles(Interface):
    #implements(INonInstallable)

    def getNonInstallableProfiles(self):
        """ """


class InsuficientOptions(Invalid):
    __doc__ = _(u'Not enought options provided')


def PossiblePolls(context):
    portal_state = api.content.get_view(
        name='plone_portal_state',
        context=context,
        request=context.REQUEST
    )
    utility = queryUtility(IPolls, name='lmu.contenttypes.polls')
    navigation_root = portal_state.navigation_root()
    polls = utility.recent_polls(context=navigation_root, show_all=False, limit=999999)  # NOQA

    values = [SimpleTerm(value='latest', title=_(u'Latest opened poll'))]
    values.extend(
        SimpleTerm(value=i.UID, title=i.Title.decode('utf-8'))
        for i in polls
    )

    return SimpleVocabulary(values)

alsoProvides(PossiblePolls, IContextSourceBinder)


class IPolls(Interface):

    """A poll."""

    def recent_polls(show_all=False, limit=5, kw={}):
        """Return recent polls."""

    def uid_for_poll(poll):
        """Return a uid for a poll."""

    def poll_by_uid(uid):
        """Return the poll for the given uid."""

    def voters_in_a_poll(poll):
        """Return the list of voters in a poll."""

    def voted_in_a_poll(poll):
        """Check if current user already voted."""

    def allowed_to_edit(poll):
        """Return True if member is allowed to edit a poll."""

    def allowed_to_view(poll):
        """Return True if user is allowed to view this poll."""

    def allowed_to_vote(poll):
        """Return True is user is allowed to vote in a poll."""

    def anonymous_vote_id(poll_uid):
        """Return a identifier for vote_id."""


class IPoll(Interface):
    """A Poll in a Plone site."""


class IStarPoll(IPoll):
    """  """


class IAgreeDisagreePoll(IPoll):
    """  """


class ILikeDislikePoll(IPoll):
    """  """


class IFreePoll(Interface):
    """A Poll Type that let you create a Poll with qquestion otion you could define by yourselfe."""

    # multivalue = schema.Bool(
    #    title = _(u"Multivalue"),
    #    description = _(u"Voters can choose several answers at the same "
    #                     "time."),
    # )

    show_results = schema.Choice(
        title=_(u'Show results'),
        description=_(
            u'How to show results.'),
        source=config.SHOW_RESULTS_OPTIONS,
        default='after_vote',  # config.SHOW_RESULTS_OPTIONS[0].value,
        required=True,
    )

    general_results_graph = schema.Choice(
        title=_(u'Graph'),
        description=_(u'Format to show the results.'),
        source=config.GENERAL_RESULT_GRAPH_OPTIONS,
        default='bar',
        required=True,
    )

    change_vote = schema.Bool(
        title=_(u'Allow to change Vote'),
        description=_(u'Allow user to change vote after a successful submit.'),
        default=False,
        required=False,
    )

    allow_anonymous = schema.Bool(
        title=_(u'Allow anonymous'),
        description=_(
            u'Allow not logged in users to vote. '
            u'The parent folder of this poll should be published before opeining the poll for this field to take effect'),  # NOQA
        default=False,
        required=False,
    )

    form.widget(options=EnhancedTextLinesFieldWidget)
    options = schema.List(
        title=_(u'Available options'),
        value_type=schema.TextLine(),
        default=[],
        required=True,
    )

    @invariant
    def validate_options(data):
        """Validate options."""
        options = data.options
        descriptions = options and [o for o in options]
        if len(descriptions) < 2:
            raise InsuficientOptions(
                _(u'You need to provide at least two options for a free poll.'))
