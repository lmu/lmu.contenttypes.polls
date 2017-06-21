# -*- coding: utf-8 -*-

import random
import time

from AccessControl import Unauthorized
from Products.CMFPlone.interfaces.syndication import ISyndicatable
#from Products.statusmessages.interfaces import IStatusMessage
#from plone.dexterity.content import Item
from plone.dexterity.content import Container
from plone import api
from plone.uuid.interfaces import IUUID
from zope.interface import implements

from lmu.contenttypes.polls.config import COOKIE_KEY
from lmu.contenttypes.polls.interfaces import IPolls
from lmu.contenttypes.polls.interfaces import IPollFolder

from logging import getLogger

log = getLogger(__name__)


class PollFolder(Container):
    implements(IPollFolder, ISyndicatable)


class Polls(object):
    """Utility methods for dealing with polls."""
    implements(IPolls)

    @property
    def ct(self):
        return api.portal.get_tool(name='portal_catalog')

    @property
    def mt(self):
        return api.portal.get_tool(name='portal_membership')

    @property
    def wt(self):
        return api.portal.get_tool(name='portal_workflow')

    @property
    def member(self):
        return self.mt.getAuthenticatedMember()

    def _query_for_polls(self, **kw):
        """Use Portal Catalog to return a list of polls."""
        kw['portal_type'] = ['Poll',
                             'Star Poll',
                             'Agree Disagree Poll',
                             'Like Dislike Poll',
                             'Free Poll']
        results = self.ct.searchResults(**kw)
        return results

    def uid_for_poll(self, poll):
        """Return a uid for a poll."""
        return IUUID(poll)

    def recent_polls(self, context=None, show_all=False, limit=5, **kw):
        """Return recent polls."""
        if context is not None:
            kw['path'] = '/'.join(context.getPhysicalPath())

        kw['sort_on'] = 'created'
        kw['sort_order'] = 'reverse'
        kw['sort_limit'] = limit
        if not show_all:
            kw['review_state'] = 'open'
        results = self._query_for_polls(**kw)
        return results[:limit]

    def poll_by_uid(self, uid, context=None):
        """Return the poll for the given uid."""
        if uid == 'latest':
            results = self.recent_polls(context=context,
                                        show_all=False,
                                        limit=1)
        else:
            kw = {'UID': uid}
            results = self._query_for_polls(**kw)
        if results:
            poll = results[0].getObject()
            return poll

    def voted_in_a_poll(self, poll, request=None):
        """Check if current user already voted."""
        anonymous_allowed = None  # poll.allow_anonymous
        poll_uid = self.uid_for_poll(poll)
        member = self.member
        member_id = member.getId()
        voters = poll.voters()

        log.debug('Voted in Poll / Allow to Vote: Check if member "%s" or "%s" has voted in Poll: %s', member_id, request.get('HTTP_EDUPERSONPRINCIPALNAME'), request.getURL())
        if api.user.is_anonymous() or member_id == 'Anonymous User':
            log.debug('Voted in Poll / Allow to Vote: Member has been identified as "%s", replace it with EDUPersonPrincipalName.', member_id)
            member_id = request.get('HTTP_EDUPERSONPRINCIPALNAME')
            log.debug('Voted in Poll / Allow to Vote: replaced with "%s" from EDUPersonPrincipalName.', member_id)
            if member_id:
                member_id = member_id.split('@')[0].strip()
            log.debug('Voted in Poll / Allow to Vote: normalized "%s" from EDUPersonPrincipalName.', member_id)

        log.debug('Voted in Poll / Allow to Vote: Update on member_id "%s".', member_id)
        if member_id and member_id != 'Anonymous User':
            log.debug('Voted in Poll / Allow to Vote: calculated member "%s" is in voters? (%s), list of voters: %s', member_id, bool(member_id in voters), voters)
            return member_id in voters
        elif anonymous_allowed and request:
            cookie = COOKIE_KEY % poll_uid
            value = request.cookies.get(cookie, '')
            if value:
                value = 'Anonymous-%s' % value in voters
            return value
        else:
            # If we cannot be sure, we will block this user from voting again
            return True

    def allowed_to_edit(self, poll):
        """Return True if member is allowed to edit a poll."""
        return self.mt.checkPermission('Modify portal content', poll) == 1

    def allowed_to_view(self, poll):
        """Return True if user is allowed to view this poll."""
        return self.mt.checkPermission('View', poll) == 1

    def allowed_to_vote(self, poll, request=None):
        """Return True is user is allowed to vote in a poll."""
        canVote = self.mt.checkPermission(
            'lmu.contenttypes.polls: Vote', poll) == 1
        if canVote:
            # User must view the poll
            # and poll must be open to allow votes
            return not self.voted_in_a_poll(poll, request)
        # All other cases shall not pass
        raise Unauthorized

    def anonymous_vote_id(self):
        """Return a identifier for vote_id."""
        vote_id = int(time.time() * 10000000) + random.randint(0, 99)
        return vote_id
