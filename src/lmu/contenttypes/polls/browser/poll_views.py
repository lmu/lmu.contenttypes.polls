# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from Acquisition import aq_inner
from Acquisition import aq_parent
from Products.CMFCore.interfaces import ISiteRoot
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from plone.app.layout.viewlets import common as base
from zope.component import getMultiAdapter

from lmu.contenttypes.polls import MessageFactory as _


class PollView(BrowserView):

    poll_star_template = ViewPageTemplateFile('templates/poll_star.pt')
    poll_like_dislike_template = ViewPageTemplateFile('templates/poll_like_dislike.pt')  # NOQA
    poll_true_not_true_template = ViewPageTemplateFile('templates/poll_true_not_true.pt')  # NOQA
    poll_free_template = ViewPageTemplateFile('templates/poll_free.pt')

    def __init__(self, context, request):
        """
        """
        super(PollView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.state = getMultiAdapter(
            (context, self.request), name=u'plone_context_state')
        self.wf_state = self.state.workflow_state()
        self.utility = context.utility
        self.poll_type = context.poll_type

    def __call__(self):
        """
        """
        env = self.request.environ
        request_type = env.get('REQUEST_METHOD', 'GET')

        if request_type == 'GET':
            if self.poll_type == 'poll_star':
                self.template = self.poll_star_template
                results = self.get_results()
                if results:
                    self.participants = results.get('total', 0)
                    self.average = 0.0
                    for option in results.get('options', []):
                        self.average += float(option['index']) * \
                            float(option['votes'])
                    if self.participants > 1:
                        self.average = self.average / self.participants
            elif self.poll_type == 'poll_true_not_true':
                self.template = self.poll_true_not_true_template

            elif self.poll_type == 'poll_like_dislike':
                self.template = self.poll_like_dislike_template

            elif self.poll_type == 'poll_free':
                self.template = self.poll_free_template
        elif request_type == 'POST':
            self.update()
            referer = env.get('HTTP_REFERER', self.context.absolute_url)
            return self.request.response.redirect(referer)
        return self.template()

    def update(self):
        """
        """
        messages = IStatusMessage(self.request)
        #context = aq_inner(self.context)
        #self.context = context

        # Handle vote
        form = self.request.form
        self.errors = []
        self.messages = []

        # if the poll is open and anonymous should vote but the parent folder
        # is private.. inform the user.

        # When the poll's container is the site's root, we do not need to
        # check the permissions.
        container = aq_parent(aq_inner(self.context))

        if 'open' == self.wf_state and not ISiteRoot.providedBy(container):
            roles = [
                r['name'] for r in
                self.context.rolesOfPermission('lmu.contenttypes.polls: Vote')
                if r['selected']]

            if 'Anonymous' not in roles and self.context.allow_anonymous:
                messages.addStatusMessage(_(
                    u"Anonymous user won't be able to vote, you forgot to "
                    u'publish the parent folder, you must sent back the poll '
                    u'to private state, publish the parent folder and open '
                    u'the poll again'), type='info')

        if 'poll.submit' in form:
            self._updateForm(form)
        # Update status messages
        for error in self.errors:
            messages.addStatusMessage(error, type='warn')
        for msg in self.messages:
            messages.addStatusMessage(msg, type='info')

        # XXX
        # if 'voting.from' in form:
        #     url = form['voting.from']
        #     self.request.RESPONSE.redirect(url)

    def _updateForm(self, form):
        INVALID_OPTION = _(u'Invalid option')
        options = form.get('options', '')
        if isinstance(options, list):
            self.errors.append(INVALID_OPTION)
        elif isinstance(options, str):
            if not options.isdigit():
                self.errors.append(INVALID_OPTION)
            else:
                options = int(options)
        if not self.errors:
            # Let's vote
            try:
                self.context.set_vote(options, self.request)
                self.messages.append(_(u'Thanks for your vote'))
                # We do this to avoid redirecting anonymous user as
                # we just sent them the cookie
                self._has_voted = True
            except Unauthorized:
                self.errors.append(_(u'You are not authorized to vote'))

    @property
    def can_vote(self):
        if hasattr(self, '_has_voted') and self._has_voted:
            # This is mainly to avoid anonymous users seeing the form again
            self.messages.addStatusMessage(
                'Anonymous Users are not allowed to vote.',
                type='warn'
            )
            return False
        utility = self.utility
        try:
            return utility.allowed_to_vote(self.context, self.request)
        except Unauthorized:
            return False

    @property
    def can_edit(self):
        utility = self.utility
        return utility.allowed_to_edit(self.context)

    @property
    def has_voted(self):
        """Return True if the current user voted in this poll."""
        if hasattr(self, '_has_voted') and self._has_voted:
            return True
        utility = self.utility
        voted = utility.voted_in_a_poll(self.context, self.request)
        return voted

    def poll_uid(self):
        """Return uid for current poll."""
        utility = self.utility
        return utility.uid_for_poll(self.context)

    def get_poll_type(self):
        return self.context.get_poll_type()

    def get_show_results(self):
        return self.context.get_show_results()

    def graph_type(self):
        if self.context.get_poll_type() == 'poll_star':
            return self.context.star_results_graph
        else:
            return self.context.general_results_graph

    def get_options(self):
        """Return available options."""
        return self.context.get_options()

    def get_wf_state(self):
        return self.wf_state

    def get_results(self):
        """Return results so far if allowed."""
        show_results = False
        context = aq_inner(self.context)
        if self.wf_state == 'open':
            show_results = show_results or context.show_results
        elif self.wf_state == 'closed':
            show_results = True
        return (show_results and context.get_results()) or None

    def fake_results(self):
        return [
            {'index': 1,
             'description': u'1 Star',
             'votes': 1,
             'percentage': 0.00662},
            {'index': 2,
             'description': u'2 Stars',
             'votes': 4,
             'percentage': 0.05298},
            {'index': 3,
             'description': u'3 Stars',
             'votes': 9,
             'percentage': 0.17881},
            {'index': 4,
             'description': u'4 Stars',
             'votes': 25,
             'percentage': 0.66225},
            {'index': 5,
             'description': u'5 Stars',
             'votes': 3,
             'percentage': 0.09934},
        ]

    def get_star_average_widget(self, example=False):
        if example:
            viewlet = StarAverageWidgetViewlet(
                self.context, self.request, None, None,
                0.71905, 3.59, 42)
        else:
            viewlet = StarAverageWidgetViewlet(
                self.context, self.request, None, None,
                self.average/5.0, self.average, self.participants)
        return viewlet.render()

    def get_star_bar_widget(self, example=False):
        if example:
            viewlet = StarBarWidgetViewlet(
                self.context, self.request, None, None,
                self.fake_results(), 42)
        else:
            results = self.get_results()
            viewlet = StarBarWidgetViewlet(
                self.context, self.request, None, None,
                results['options'], results['total'])
        return viewlet.render()

    def get_star_numbers_widget(self, example=False):
        if example:
            viewlet = StarNumbersWidgetViewlet(
                self.context, self.request, None, None,
                self.fake_results(), 42)
        else:
            results = self.get_results()
            viewlet = StarNumbersWidgetViewlet(
                self.context, self.request, None, None,
                results['options'], results['total'])
        return viewlet.render()


class StarAverageWidgetViewlet(base.ViewletBase):

    template = ViewPageTemplateFile('templates/poll_star_average_widget.pt')

    def __init__(self, context, request, portal, manager,
                 average, star_average, participants):
        """
        """
        super(StarAverageWidgetViewlet, self).__init__(
            context, request, portal, manager)
        self.context = context
        self.request = request
        self.average = average * 100.0
        self.participants = participants
        self.star_average = star_average

    def render(self):
        return self.template()


class StarBarWidgetViewlet(base.ViewletBase):

    template = ViewPageTemplateFile('templates/poll_star_bar_widget.pt')

    def __init__(self, context, request, portal, manager,
                 results, participants=0):
        """
        """
        super(StarBarWidgetViewlet, self).__init__(context, request, portal, manager)  # NOQA
        self.context = context
        self.request = request
        self.results = results
        self.participants = participants

    def render(self):
        for option in self.results:
            setattr(self, 'result{index}{name}'.format(
                index=option['index'], name='par'), option['votes'])
            per = option['percentage']
            setattr(self, 'result{index}{name}'.format(
                index=option['index'], name='per'), per*100.0)
            setattr(self, 'result{index}{name}'.format(
                index=option['index'], name='style'),
                'width: {per}%;'.format(per=per*100.0))
        return self.template()


class StarNumbersWidgetViewlet(StarBarWidgetViewlet):

    template = ViewPageTemplateFile('templates/poll_star_numbers_widget.pt')
