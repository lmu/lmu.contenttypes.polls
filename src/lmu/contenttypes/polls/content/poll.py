# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from plone.dexterity.content import Item
#from plone.dexterity.content import Container

from plone import api
from plone.i18n.normalizer import idnormalizer
from plone.i18n.normalizer import urlnormalizer
from z3c.form.interfaces import IValidator
from z3c.form.validator import SimpleFieldValidator
from zope.annotation.interfaces import IAnnotations
from zope.component import queryUtility
from zope.interface import implements

from lmu.contenttypes.polls import MessageFactory as _
from lmu.contenttypes.polls.config import COOKIE_KEY
from lmu.contenttypes.polls.config import MEMBERS_ANNO_KEY
from lmu.contenttypes.polls.config import PERMISSION_VOTE
from lmu.contenttypes.polls.config import VOTE_ANNO_KEY
from lmu.contenttypes.polls.interfaces import IPoll
from lmu.contenttypes.polls.interfaces import IStarPoll
from lmu.contenttypes.polls.interfaces import IAgreeDisagreePoll
from lmu.contenttypes.polls.interfaces import ILikeDislikePoll
from lmu.contenttypes.polls.interfaces import IFreePoll
from lmu.contenttypes.polls.interfaces import IPolls
from lmu.contenttypes.polls.interfaces import InsuficientOptions

from logging import getLogger

log = getLogger(__name__)


class Poll(Item):
    """A Poll in a Plone site."""
    implements(IPoll)

    __ac_permissions__ = (
        (PERMISSION_VOTE, ('set_vote', '_set_voter', )),
    )

    @property
    def annotations(self):
        return IAnnotations(self)

    @property
    def utility(self):
        utility = queryUtility(IPolls, name='lmu.contenttypes.polls')
        return utility

    def get_show_results(self):
        return self.show_results

    def _get_votes(self):
        """Return votes in a dict format."""
        votes = {'options': [],
                 'total': 0}
        for option in self.get_options():
            index = option.get('option_id')
            description = option.get('description')
            token = option.get('token')
            option_votes = self.annotations.get(VOTE_ANNO_KEY % index, 0)
            votes['options'].append({'index': index,
                                     'description': description,
                                     'token': token,
                                     'votes': option_votes,
                                     'percentage': 0.0})
            votes['total'] = votes['total'] + option_votes
        for option in votes['options']:
            if option['votes']:
                option['percentage'] = option['votes'] / float(votes['total'])
        return votes

    def get_results(self):
        """Return results so far."""
        return self._get_votes()

    def _validate_vote(self, options=[]):
        """Check if passed options are available here."""
        available_options = [o['option_id'] for o in self.get_options()]
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
        log.info('_set_voter: Try to set voter "%s" for Poll: %s', member_id, request.getURL())
        if api.user.is_anonymous() or member_id == 'Anonymous User':
            member_id = request.get('HTTP_EDUPERSONPRINCIPALNAME')
            if member_id:
                member_id = member_id.splitt('@')[0].strip()
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

        if member_id and member_id != 'Anonymous User':
            log.info('_set_voter: Set voter "%s" for Poll: %s', member_id, request.getURL())
            voters.append(member_id)
            annotations[MEMBERS_ANNO_KEY] = voters
            return True

    def _remove_voter(self, request=None):
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
            voters.remove(member_id)
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
        if not self._validate_vote(options):
            return False
        if not isinstance(options, list):
            options = [options, ]
        if not self._set_voter(request):
            # We failed to set voter, so we will not compute its votes
            return False
        # set vote in annotation storage
        for option in options:
            vote_key = VOTE_ANNO_KEY % option
            votes = annotations.get(vote_key, 0)
            annotations[vote_key] = votes + 1
        return True

    def remove_vote(self, options=[], request=None):
        """Set a vote on this poll."""
        annotations = self.annotations

        for option in options:
            vote_key = VOTE_ANNO_KEY % option
            votes = annotations.get(vote_key, 0)
            annotations[vote_key] = votes + 1
        return True


class StarPoll(Poll):
    """ """
    implements(IStarPoll, IPoll)

    def get_options(self):
        """Return available options."""
        return [
            {'option_id': 1, 'token': '', 'description': ''},
            {'option_id': 2, 'token': '', 'description': ''},
            {'option_id': 3, 'token': '', 'description': ''},
            {'option_id': 4, 'token': '', 'description': ''},
            {'option_id': 5, 'token': '', 'description': ''}
        ]


class AgreeDisagreePoll(Poll):
    """ """
    implements(IAgreeDisagreePoll, IPoll)

    def get_options(self):
        """Return available options."""
        return [
            {'option_id': 1, 'token': 'agree', 'description': _('Agree')},
            {'option_id': 2, 'token': 'disagree', 'description': _('Disagree')}
        ]


class LikeDislikePoll(Poll):
    """ """
    implements(ILikeDislikePoll, IPoll)

    def get_options(self):
        """Return available options."""
        return [
            {'option_id': 1, 'token': 'like', 'description': _('Like')},
            {'option_id': 2, 'token': 'dislike', 'description': _('Dislike')}
        ]


class FreePoll(Poll):
    """ """
    implements(IFreePoll, IPoll)

    def get_options(self):
        """Return available options."""
        options = []
        index = 1
        for option in self.options:
            options.append({'option_id': index, 'token': 'free-' + str(index), 'description': option})
            index += 1
        return options


class AtLeastTwoOptionsValidator(SimpleFieldValidator):
    implements(IValidator)

    def validate(self, value):
        """Validate options."""
        super(AtLeastTwoOptionsValidator, self).validate(value)
        if value is not None:
            descriptions = value and [o for o in value]
            if len(descriptions) < 2:
                log.info(u'You need to provide at least two options for a free poll.')
                #raise InsuficientOptions(_(u'You need to provide at least two options for a free poll.'))

    def validate_options(data):
        """Validate options."""
        options = data.options
        descriptions = options and [o for o in options]
        if len(descriptions) < 2:
            log.info(u'You need to provide at least two options for a free poll.')
            raise InsuficientOptions(_(u'You need to provide at least two options for a free poll.'))
