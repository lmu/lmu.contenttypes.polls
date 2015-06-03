# -*- coding: utf-8 -*-

from Acquisition import aq_parent
from Products.CMFCore.interfaces import IActionSucceededEvent
from Products.CMFCore.interfaces import ISiteRoot
from zope.component import getGlobalSiteManager

from lmu.contenttypes.polls.config import ALL_ROLES
from lmu.contenttypes.polls.config import MEMBERS_ANNO_KEY
from lmu.contenttypes.polls.config import PERMISSION_VOTE
from lmu.contenttypes.polls.config import VOTE_ANNO_KEY
from lmu.contenttypes.polls.poll import IPoll


gsm = getGlobalSiteManager()


def fix_permissions(poll, event):
    """Fix permission on poll object if allow_anonymous is enabled."""
    if event.action in ['open', ]:
        parent = aq_parent(poll)
        parent_view_roles = parent.rolesOfPermission('View')
        parent_view_roles = [
            r['name'] for r in parent_view_roles if r['selected']]
        # Poll has been opened
        import ipdb; ipdb.set_trace()
        allow_anonymous = poll.allow_anonymous
        parent_is_root = ISiteRoot.providedBy(parent)
        parent_allow_anon = 'Anonymous' in parent_view_roles
        if (parent_allow_anon or parent_is_root) and allow_anonymous:
            poll.manage_permission(PERMISSION_VOTE,
                                   ALL_ROLES,
                                   acquire=0)

gsm.registerHandler(fix_permissions, (IPoll, IActionSucceededEvent))


def remove_votes(poll, event):
    """Remove existing votes on poll object if reject transaction happens."""
    if event.action in ['reject', ]:
        options = [o.get('option_id') for o in poll.getOptions()]
        annotations = poll.annotations
        # Erase Voters
        annotations[MEMBERS_ANNO_KEY] = []
        # Erase Votes
        for option in options:
            annotations[VOTE_ANNO_KEY % option] = 0

gsm.registerHandler(remove_votes, (IPoll, IActionSucceededEvent))
