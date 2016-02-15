# -*- coding: utf-8 -*-
import random

from datetime import datetime

from AccessControl import Unauthorized
from Acquisition import aq_inner
#from Acquisition import aq_parent
#from Products.CMFCore.interfaces import ISiteRoot
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from plone.app.layout.viewlets import common as base
from zope.component import getMultiAdapter
from zope.component import queryUtility

from lmu.policy.base.browser.content_listing import _IncludeMixin
from lmu.policy.base.browser.utils import isDBReadOnly as uIsDBReadOnly

from lmu.contenttypes.polls import MessageFactory as _
#from lmu.contenttypes.polls.interfaces import IPoll
from lmu.contenttypes.polls.interfaces import IPolls

from logging import getLogger

log = getLogger(__name__)


def str2bool(v):
    return v is not None and v.lower() in ['true', '1']


class ListingView(BrowserView):

    template = ViewPageTemplateFile('templates/listing_view.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

#        RESPONSE = request.response
#        RESPONSE.setHeader('X-Theme-Disabled', 'False')
#        RESPONSE.setHeader('X-Theme-Enabled', 'True')
#
#        RESPONSE.setHeader('X-Theme-Disabled', 'False')
#        RESPONSE.setHeader('X-Theme-Enabled', 'True')

    def __call__(self):
        return self.template()


class BaseView(BrowserView):

    def __init__(self, context, request):
        """
        """
        super(BaseView, self).__init__(context, request)
        self.context = context
        self.request = request

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
        #container = aq_parent(aq_inner(self.context))

        #if 'open' == self.wf_state and not ISiteRoot.providedBy(container):
            # roles = [
            #     r['name'] for r in
            #     self.context.rolesOfPermission('lmu.contenttypes.polls: Vote')
            #     if r['selected']]

            # if 'Anonymous' not in roles and self.context.allow_anonymous:
            #     messages.addStatusMessage(_(
            #         u"Anonymous user won't be able to vote, you forgot to "
            #         u'publish the parent folder, you must sent back the poll '
            #         u'to private state, publish the parent folder and open '
            #         u'the poll again'), type='info')

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
                #self.messages.append(_(u'Thanks for your vote'))
                # We do this to avoid redirecting anonymous user as
                # we just sent them the cookie
                self._has_voted = True
            except Unauthorized:
                #self.errors.append(_(u'You are not authorized to vote'))
                pass

    def handleRedirect(self):
        env = self.request.environ
        referer = str(env.get('HTTP_REFERER', self.context.absolute_url()))
        referer += '#feedback?vote=' + str(random.getrandbits(100)) + '&vote-timestamp=' + str(datetime.now().isoformat())
        return self.request.response.redirect(referer)

    def isDBReadOnly(self):
        return uIsDBReadOnly()


class CurrentPollView(BaseView, _IncludeMixin):

    template = ViewPageTemplateFile('templates/current_poll_view.pt')

    def __call__(self):
        self.utility = queryUtility(IPolls, name='lmu.contenttypes.polls')
        self.open_polls = self.utility.recent_polls()
        self.closed_polls = self.utility.recent_polls(show_all=True,
                                                      review_state='closed')
        super(CurrentPollView, self).__call__()

        if len(self.open_polls) == 1:
            poll = self.open_polls[0].getObject()
            return poll.restrictedTraverse('@@poll_base_view')()
        elif len(self.open_polls) <= 0 and len(self.closed_polls) <= 0:
            return _(u"No active or closed Polls avalible")
        return self.template()


class PollBaseView(BaseView):

    poll_star_template = ViewPageTemplateFile('templates/poll_star.pt')
    poll_like_dislike_template = ViewPageTemplateFile('templates/poll_like_dislike.pt')
    poll_agree_disagree_template = ViewPageTemplateFile('templates/poll_agree_disagree.pt')
    poll_free_template = ViewPageTemplateFile('templates/poll_free.pt')

    def __init__(self, context, request):
        """
        """
        self.context = context
        self.request = request
        self.state = getMultiAdapter(
            (context, self.request), name=u'plone_context_state')
        self.wf_state = self.state.workflow_state()
        self.utility = context.utility
        self.poll_type = context.portal_type
        omit = self.request.get('omit')
        self.omit = str2bool(omit)
        self.heading_level = 'h3'
        super(PollBaseView, self).__init__(context, request)

    def __call__(self):
        """
        """
        env = self.request.environ
        request_type = env.get('REQUEST_METHOD', 'GET')

        if request_type == 'GET':
            view_class = self.request.steps[-1:][0]
            if view_class in ['current_poll.include', ' poll_base_view']:
                self.heading_level = 'h3'
                REQUEST = self.context.REQUEST
                RESPONSE = REQUEST.RESPONSE
                RESPONSE.setHeader('X-Theme-Disabled', 'True')
            else:
                self.heading_level = 'h1'
            if self.poll_type == 'Star Poll':
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
            elif self.poll_type == 'Agree Disagree Poll':
                self.template = self.poll_agree_disagree_template

            elif self.poll_type == 'Like Dislike Poll':
                self.template = self.poll_like_dislike_template

            elif self.poll_type == 'Free Poll':
                self.template = self.poll_free_template
            else:
                log.warn('Unknown Poll Type selected.')
            #    import ipdb; ipdb.set_trace()
        elif request_type == 'POST':
            self.update()
            return self.handleRedirect()
        return self.template()

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
        return self.poll_type

    def get_show_results(self):
        return self.context.get_show_results()

    def graph_type(self):
        return self.context.result_diagramm

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

    def fake_star_results(self):
        return [
            {'index': 1,
             'description': _(u'1 Star'),
             'token': 'star-1',
             'votes': 1,
             'percentage': 0.00662},
            {'index': 2,
             'description': _(u'2 Stars'),
             'token': 'star-1',
             'votes': 4,
             'percentage': 0.05298},
            {'index': 3,
             'description': _(u'3 Stars'),
             'token': 'star-3',
             'votes': 9,
             'percentage': 0.17881},
            {'index': 4,
             'description': _(u'4 Stars'),
             'token': 'star-4',
             'votes': 25,
             'percentage': 0.66225},
            {'index': 5,
             'description': _(u'5 Stars'),
             'token': 'star-5',
             'votes': 3,
             'percentage': 0.09934},
        ]

    def fake_agree_results(self):
        return [
            {'index': 1,
             'description': _(u'Agree'),
             'token': 'agree',
             'votes': 22,
             'percentage': 0.52381},
            {'index': 2,
             'description': _(u'Disagree'),
             'token': 'disagree',
             'votes': 20,
             'percentage': 0.47619},
        ]

    def fake_free_results(self):
        fake_result = []
        index = 1
        elems = len(self.context.options)
        total = 42
        rest = total
        for option in self.context.options:
            fake_votes = random.randint(0, rest)
            if index == elems:
                fake_votes = rest
            per = float(fake_votes)/float(total)
            fake_result.append({
                'index': index,
                'description': option,
                'token': 'free-' + str(index),
                'votes': fake_votes,
                'percentage': per,
            })
            rest = rest - fake_votes
            index += 1
        return fake_result

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
                self.fake_star_results(), 42)
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
                self.fake_star_results(), 42)
        else:
            results = self.get_results()
            viewlet = StarNumbersWidgetViewlet(
                self.context, self.request, None, None,
                results['options'], results['total'])
        return viewlet.render()

    def get_two_option_bar_widget(self, example=False):
        if example:
            viewlet = TwoOptionBarWidgetViewlet(
                self.context, self.request, None, None,
                self.fake_agree_results(), 42)
        else:
            results = self.get_results()
            viewlet = TwoOptionBarWidgetViewlet(
                self.context, self.request, None, None,
                results['options'], results['total'])
        return viewlet.render()

    def get_multi_option_bar_widget(self, example=False):
        if example:
            viewlet = MultiOptionBarWidgetViewlet(
                self.context, self.request, None, None,
                self.fake_free_results(), 42)
        else:
            results = self.get_results()
            viewlet = MultiOptionBarWidgetViewlet(
                self.context, self.request, None, None,
                results['options'], results['total'])
        return viewlet.render()


class PollView(PollBaseView):

    template = ViewPageTemplateFile('templates/poll.pt')

    def __init__(self, context, request):
        """
        """
        super(PollView, self).__init__(context, request)
        #import ipdb; ipdb.set_trace()
        self.context = context
        self.request = request
        self.state = getMultiAdapter(
            (context, self.request), name=u'plone_context_state')
        self.wf_state = self.state.workflow_state()
        self.utility = context.utility

        env = self.request.environ
        self.request_type = env.get('REQUEST_METHOD', 'GET')
        self.results = self.get_results()

    def __call__(self):
        """
        """
        if self.request_type == 'GET':
            base_view = self.context.restrictedTraverse('@@poll_base_view')
            #base_view = PollBaseView(self.context, self.request)
            self.base_view = base_view()

            view_class = self.request.steps[-1:][0]
            if view_class in ['current_poll', ' poll_base_view']:
                self.heading_level = 'h3'
            else:
                self.heading_level = 'h1'

            if self.results:
                self.participants = self.results.get('total', 0)

        elif self.request_type == 'POST':
            self.update()
            return self.handleRedirect()
        #import ipdb;ipdb.set_trace()
        return self.template(self)


class StarPollView(PollView):

    template = ViewPageTemplateFile('templates/poll_star.pt')

    def __call__(self):
        """
        """

        #import ipdb; ipdb.set_trace()
        if self.request_type == 'GET':
            if self.results:
                self.average = 0.0
                for option in self.results.get('options', []):
                    self.average += float(option['index']) * \
                        float(option['votes'])
                if self.participants > 1:
                    self.average = self.average / self.participants
        return super(StarPollView, self).__call__()


class AgreeDisagreePollView(PollView):

    template = ViewPageTemplateFile('templates/poll_agree_disagree.pt')

    def __call__(self):
        """
        """
        self.template = ViewPageTemplateFile('templates/poll_agree_disagree.pt')
        if self.request_type == 'GET':
            if self.results:
                self.average = 0.0
                for option in self.results.get('options', []):
                    self.average += float(option['index']) * \
                        float(option['votes'])
                if self.participants > 1:
                    self.average = self.average / self.participants
        return super(AgreeDisagreePollView, self).__call__()


class LikeDislikePollView(PollView):

    template = ViewPageTemplateFile('templates/poll_like_dislike.pt')

    def __call__(self):
        """
        """
        if self.request_type == 'GET':
            if self.results:
                self.average = 0.0
                for option in self.results.get('options', []):
                    self.average += float(option['index']) * \
                        float(option['votes'])
                if self.participants > 1:
                    self.average = self.average / self.participants
        return super(LikeDislikePollView, self).__call__()


class FreePollView(PollView):

    template = ViewPageTemplateFile('templates/poll_free.pt')

    def __call__(self):
        """
        """
        self.template = ViewPageTemplateFile('templates/poll_free.pt')
        if self.request_type == 'GET':
            if self.results:
                self.average = 0.0
                for option in self.results.get('options', []):
                    self.average += float(option['index']) * \
                        float(option['votes'])
                if self.participants > 1:
                    self.average = self.average / self.participants
        return super(FreePollView, self).__call__()


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
        self.star_average = round(star_average, 1)

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
                index=option['index'], name='per'), round(per*100.0, 1))
            setattr(self, 'result{index}{name}'.format(
                index=option['index'], name='style'),
                'width: {per}%;'.format(per=per*100.0))
        return self.template()


class StarNumbersWidgetViewlet(StarBarWidgetViewlet):

    template = ViewPageTemplateFile('templates/poll_star_numbers_widget.pt')


class TwoOptionBarWidgetViewlet(base.ViewletBase):

    template = ViewPageTemplateFile('templates/two_option_bar_widget.pt')

    def __init__(self, context, request, portal, manager,
                 results, participants=0):
        """
        """
        super(TwoOptionBarWidgetViewlet, self).__init__(context, request, portal, manager)  # NOQA
        self.context = context
        self.request = request
        self.results = results
        self.participants = participants

    def render(self):
        for option in self.results:
            setattr(self, 'result{index}{name}'.format(index=option['index'], name='option'), option['description'])
            setattr(self, 'result{index}{name}'.format(index=option['index'], name='token'), option['token'])
            setattr(self, 'result{index}{name}'.format(index=option['index'], name='par'), option['votes'])
            per = option['percentage']
            setattr(self, 'result{index}{name}'.format(index=option['index'], name='per'), round(per*100.0, 1))
            setattr(self, 'result{index}{name}'.format(index=option['index'], name='style'), 'width: {per}%;'.format(per=per*100.0))
        return self.template()


class MultiOptionBarWidgetViewlet(base.ViewletBase):

    template = ViewPageTemplateFile('templates/multi_option_bar_widget.pt')

    def __init__(self, context, request, portal, manager,
                 results, participants=0):
        """
        """
        super(MultiOptionBarWidgetViewlet, self).__init__(context, request, portal, manager)  # NOQA
        self.context = context
        self.request = request
        self.results = results
        self.participants = participants

    def render(self):
        self.options = []
        for option in self.results:
            per = option['percentage']
            self.options.append({
                'option': option['description'],
                'token': option['token'],
                'par': option['votes'],
                'per': round(per*100.0, 1),
                'style': 'width: {per}%;'.format(per=per*100.0)
            })
        return self.template()
