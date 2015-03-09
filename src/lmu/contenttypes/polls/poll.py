# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from plone.directives import dexterity
from zope.annotation.interfaces import IAnnotations
from zope.component import queryUtility
from zope.interface import implements

from lmu.contenttypes.polls.config import COOKIE_KEY
from lmu.contenttypes.polls.config import MEMBERS_ANNO_KEY
from lmu.contenttypes.polls.config import PERMISSION_VOTE
from lmu.contenttypes.polls.config import VOTE_ANNO_KEY
from lmu.contenttypes.polls.interfaces import IPoll
from lmu.contenttypes.polls.interfaces import IPolls


class Poll(dexterity.Item):
    """A Poll in a Plone site."""
    implements(IPoll)

    __ac_permissions__ = (
        (PERMISSION_VOTE, ('setVote', '_setVoter', )),
    )

    @property
    def annotations(self):
        return IAnnotations(self)

    @property
    def utility(self):
        utility = queryUtility(IPolls, name='lmu.contenttypes.polls')
        return utility

    def get_poll_type(self):
        return self.poll_type

    def get_options(self):
        """Return available options."""
        options = []
        if self.poll_type == 'poll_star':
            options = [
                {'option_id': '1', 'description': ''},
                {'option_id': '2', 'description': ''},
                {'option_id': '3', 'description': ''},
                {'option_id': '4', 'description': ''},
                {'option_id': '5', 'description': ''}
            ]
        elif self.poll_type == 'poll_free':
            for option in self.options:
                options.append({
                    'option_id': option.lower(),
                    'description': option
                })

        return options

    def _get_votes(self):
        """Return votes in a dict format."""
        votes = {'options': [],
                 'total': 0}
        for option in self.getOptions():
            index = option.get('option_id')
            description = option.get('description')
            option_votes = self.annotations.get(VOTE_ANNO_KEY % index, 0)
            votes['options'].append({'description': description,
                                     'votes': option_votes,
                                     'percentage': 0.0})
            votes['total'] = votes['total'] + option_votes
        for option in votes['options']:
            if option['votes']:
                option['percentage'] = option['votes'] / float(votes['total'])
        return votes

    def get_results(self):
        """Return results so far."""
        votes = self._getVotes()
        all_results = []
        for item in votes['options']:
            all_results.append((item['description'],
                                item['votes'],
                                item['percentage']))
        return all_results

    def _validate_vote(self, options=[]):
        """Check if passed options are available here."""
        available_options = [o['option_id'] for o in self.getOptions()]
        if isinstance(options, list):
            # TODO: Allow multiple options
            # multivalue = self.multivalue
            return False
        else:
            return options in available_options

    def _set_voter(self, request=None):
        """Mark this user as a voter."""
        utility = self.utility
        annotations = self.annotations
        voters = self.voters()
        member = utility.member
        member_id = member.getId()
        if not member_id and request:
            poll_uid = utility.uid_for_poll(self)
            cookie = COOKIE_KEY % str(poll_uid)
            expires = 'Wed, 19 Feb 2020 14:28:00 GMT'  # XXX: why hardcoded?
            vote_id = str(utility.anonymous_vote_id())
            request.response[cookie] = vote_id
            request.response.setCookie(cookie,
                                       vote_id,
                                       path='/',
                                       expires=expires)
            member_id = 'Anonymous-%s' % vote_id

        if member_id:
            voters.append(member_id)
            annotations[MEMBERS_ANNO_KEY] = voters
            return True

    def voters(self):
        annotations = self.annotations
        voters = annotations.get(MEMBERS_ANNO_KEY, [])
        return voters

    @property
    def total_votes(self):
        """Return the number of votes so far."""
        votes = self._getVotes()
        return votes['total']

    def set_vote(self, options=[], request=None):
        """Set a vote on this poll."""
        annotations = self.annotations
        utility = self.utility
        try:
            if not utility.allowed_to_vote(self, request):
                return False
        except Unauthorized:
            raise Unauthorized
        if not self._validateVote(options):
            return False
        if not isinstance(options, list):
            options = [options, ]
        if not self._setVoter(request):
            # We failed to set voter, so we will not compute its votes
            return False
        # set vote in annotation storage
        for option in options:
            vote_key = VOTE_ANNO_KEY % option
            votes = annotations.get(vote_key, 0)
            annotations[vote_key] = votes + 1
        return True
