# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone import api
from plone.app.portlets.portlets import base
from plone.memoize.instance import memoize
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletRenderer
from plone.portlets.interfaces import IPortletRetriever
from zope.component import ComponentLookupError
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.formlib import form
from zope.interface import implements

from lmu.contenttypes.polls.interfaces import IPolls
from lmu.contenttypes.polls.interfaces import IVotePortlet
from lmu.contenttypes.polls import MessageFactory as _


class PollPortletRender(base.Renderer):
    """This methods allow to use the portlet render in a view."""

    def get_portlet_manager(self, column=''):
        """Return one of default Plone portlet managers.

        @param column: "plone.leftcolumn" or "plone.rightcolumn"

        @return: plone.portlets.interfaces.IPortletManagerRenderer instance
        """
        if column:
            try:
                manager = getUtility(IPortletManager, name=column)
            except ComponentLookupError:
                # Happens when using polls in a panel from collective.panels
                manager = None
        else:
            manager = getUtility(IPortletManager, name='plone.rightcolumn')
            if not manager:
                manager = getUtility(IPortletManager, name='plone.leftcolumn')
        return manager

    def render_portlet(self, context, request, view, manager, interface):
        """Render a portlet defined in external location.

        .. note ::

            Portlets can be idenfied by id (not user visible)
            or interface (portlet class). This method supports look up
            by interface and will return the first matching portlet with
            this interface.

        @param context: Content item reference where portlet appear

        @param manager: IPortletManagerRenderer instance

        @param view: Current view or None if not available

        @param interface: Marker interface class we use to identify
            the portlet. E.g. IFacebookPortlet

        @return: Rendered portlet HTML as a string, or empty string if
            portlet not found
        """
        if manager is None:
            return ''

        retriever = getMultiAdapter((context, manager), IPortletRetriever)

        portlets = retriever.getPortlets()

        assignment = None

        for portlet in portlets:

            # portlet is {'category': 'context',
            # 'assignment': <FacebookLikeBoxAssignment at facebook-like-box>,
            # 'name': u'facebook-like-box',
            # 'key': '/isleofback/sisalto/huvit-ja-harrasteet
            # Identify portlet by interface provided by assignment
            if interface.providedBy(portlet['assignment']):
                assignment = portlet['assignment']
                break

        if assignment is None:
            # Did not find a portlet
            return ''

        # - A special type of content provider, IPortletRenderer, knows how to
        # render each type of portlet. The IPortletRenderer should be a
        # multi-adapter from (context, request, view, portlet manager,
        #                     data provider).

        renderer = queryMultiAdapter(
            (context, request, view, manager, assignment),
            IPortletRenderer
        )

        # Make sure we have working acquisition chain
        renderer = renderer.__of__(context)

        if renderer is None:
            raise RuntimeError(
                'No portlet renderer found for portlet assignment: ' +
                str(assignment))

        renderer.update()
        # Does not check visibility here... force render always
        html = renderer.render()

        return html

    def render(self):
        """Render a portlet from another page in-line to this page.

        Does not render other portlets in the same portlet manager.
        """
        context = self.context.aq_inner
        request = self.request
        view = self

        # Alternatively, you can directly query your custom portlet manager
        # by interface
        from collective.polls.portlet.voteportlet import IVotePortlet
        column = self.request['column'] if 'column' in self.request else ''
        manager = self.get_portlet_manager(column)

        html = self.render_portlet(context, request, view,
                                   manager, IVotePortlet)
        return html


class Assignment(base.Assignment):
    """Portlet assignment.

    This is what is actually managed through the portlets UI and associated
    with columns.
    """
    implements(IVotePortlet)

    poll = None
    header = u''
    show_total = True
    show_closed = True
    link_poll = True

    def __init__(self, poll=u'latest', header=u'', show_total=True,
                 show_closed=False, link_poll=True):
        self.header = header
        self.poll = poll
        self.show_total = show_total
        self.show_closed = show_closed
        self.link_poll = link_poll

    @property
    def title(self):
        """Return the title of the portlet in the 'manage portlets' screen."""
        return _(u'Voting portlet')


class Renderer(base.Renderer):

    """Portlet renderer.

    This is registered in configure.zcml. The referenced page template is
    rendered, and the implicit variable 'view' will refer to an instance
    of this class. Other methods can be added and referenced in the template.
    """

    render = ViewPageTemplateFile('browser/templates/voteportlet.pt')

    @property
    def utility(self):
        """Access to IPolls utility."""
        utility = queryUtility(IPolls, name='lmu.contenttypes.polls')
        return utility

    def portlet_manager_name(self):
        column = self.manager.__name__
        # Check that we can reach this manager.  If this does not
        # work, we cannot refresh the portlet.  This happens when
        # using polls in a panel from lmu.contenttypes.panels and possibly
        # in other situations.  We will not activate the ajax portlet
        # refresh then.
        try:
            getUtility(IPortletManager, name=column)
        except ComponentLookupError:
            return ''
        return column

    @memoize
    def poll(self):
        portal_state = api.content.get_view(
            name='plone_portal_state',
            context=self.context,
            request=self.context.REQUEST
        )
        navigation_root = portal_state.navigation_root()
        utility = self.utility
        uid = self.data.poll
        poll = utility.poll_by_uid(uid, context=navigation_root)
        if not poll and self.data.show_closed:
            # if we have no open poll, try closed ones
            results = utility.recent_polls(
                context=navigation_root,
                show_all=True,
                limit=1,
                review_state='closed'
            )
            poll = results and results[0].getObject() or None
        return poll

    def poll_uid(self):
        """Return uid for current poll."""
        utility = self.utility
        return utility.uid_for_poll(self.poll())

    def getVotingResults(self):
        poll = self.poll()
        if poll.show_results:
            return poll.getResults()
        else:
            return None

    @property
    def can_vote(self):
        utility = self.utility
        poll = self.poll()
        try:
            return utility.allowed_to_vote(poll, self.request)
        except Unauthorized:
            return False

    @property
    def available(self):
        utility = self.utility
        poll = self.poll()
        if poll:
            can_view = utility.allowed_to_view(poll)
            # Do not show this portlet in the poll context
            return can_view and not (poll == self.context)
        return False

    def is_closed(self):
        state = self.context.portal_workflow.getInfoFor(
            self.poll(), 'review_state')
        return state == 'closed'


class AddForm(base.AddForm):

    """Portlet add form.

    This is registered in configure.zcml. The form_fields variable tells
    zope.formlib which fields to display. The create() method actually
    constructs the assignment that is being added.
    """

    form_fields = form.Fields(IVotePortlet)

    def create(self, data):
        return Assignment(**data)


class EditForm(base.EditForm):

    """Portlet edit form.

    This is registered with configure.zcml. The form_fields variable tells
    zope.formlib which fields to display.
    """

    form_fields = form.Fields(IVotePortlet)
