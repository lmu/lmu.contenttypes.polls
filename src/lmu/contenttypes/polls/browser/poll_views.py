# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from Acquisition import aq_inner
from Acquisition import aq_parent
from Products.CMFCore.interfaces import ISiteRoot
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from plone.dexterity.browser import add
from plone.dexterity.browser import edit
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
                return self.poll_star_template()
            elif self.poll_type == 'poll_true_not_true':
                return self.poll_true_not_true_template()

            elif self.poll_type == 'poll_like_dislike':
                return self.poll_like_dislike_template()

            elif self.poll_type == 'poll_free':
                return self.poll_free_template()
        elif request_type == 'POST':
            #import ipdb; ipdb.set_trace()
            self.update()
            referer = env.get('HTTP_REFERER', self.context.absolte_url)
            return self.request.response.redirect(referer)

        else:
            pass

    def update(self):
        """
        """
        super(PollView, self).update()
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
                self.context.setVote(options, self.request)
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

# class PollAddForm(add.DefaultAddForm):
#     """Form to handle creation of new Polls."""

#     def create(self, data):
#         options = data['options']
#         new_data = []
#         for (index, option) in enumerate(options):
#             option_new = {}
#             option_new['option_id'] = index
#             option_new['description'] = option
#             new_data.append(option_new)
#         data['options'] = new_data
#         return super(PollAddForm, self).create(data)


# class PollEditForm(edit.DefaultEditForm):
#     """Form to handle edition of existing polls."""

#     def updateWidgets(self):
#         """Update form widgets to hide column option_id from end user."""
#         super(PollEditForm, self).updateWidgets()

#         self.widgets['options'].allow_reorder = True
#         data = ''
#         for option in self.widgets['options'].value.split('\n'):
#             if data:
#                 data += '\n'
#             if option.strip().startswith('{'):
#                 new_val = eval(option)
#                 data += new_val['description']
#             else:
#                 data = option
#         self.widgets['options'].value = data

#     def applyChanges(self, data):
#         options = data['options']
#         new_data = []
#         for (index, option) in enumerate(options):
#             option_new = {}
#             option_new['option_id'] = index
#             option_new['description'] = option
#             new_data.append(option_new)
#         data['options'] = new_data
#         super(PollEditForm, self).applyChanges(data)
