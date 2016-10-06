# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from indico.core.db.sqlalchemy import db, PyIntEnum, UTCDateTime
from indico.util.date_time import now_utc
from indico.util.i18n import _
from indico.util.string import format_repr, return_ascii
from indico.util.struct.enum import TitledIntEnum


class AbstractAction(TitledIntEnum):
    __titles__ = [None, _("Accept"), _("Reject"), _("Merge"), _("Change track"), _("Mark as duplicate")]
    accept = 1
    reject = 2
    change_tracks = 3
    mark_as_duplicate = 4
    merge = 5


class AbstractReview(db.Model):
    """Represents an abstract review, emitted by a reviewer"""

    __tablename__ = 'abstract_reviews'
    __table_args__ = (db.UniqueConstraint('abstract_id', 'user_id', 'track_id'),
                      db.CheckConstraint("proposed_action = {} OR (proposed_contribution_type_id IS NULL)"
                                         .format(AbstractAction.accept), name='prop_contrib_id_only_accepted'),
                      db.CheckConstraint("(proposed_action IN ({}, {})) = (proposed_related_abstract_id IS NOT NULL)"
                                         .format(AbstractAction.mark_as_duplicate, AbstractAction.merge),
                                         name='prop_abstract_id_only_duplicate_merge'),
                      {'schema': 'event_abstracts'})

    id = db.Column(
        db.Integer,
        primary_key=True
    )
    abstract_id = db.Column(
        db.Integer,
        db.ForeignKey('event_abstracts.abstracts.id'),
        index=True,
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.users.id'),
        index=True,
        nullable=False
    )
    track_id = db.Column(
        db.Integer,
        db.ForeignKey('events.tracks.id'),
        index=True,
        nullable=True
    )
    created_dt = db.Column(
        UTCDateTime,
        nullable=False,
        default=now_utc,
    )
    modified_dt = db.Column(
        UTCDateTime,
        nullable=True
    )
    comment = db.Column(
        db.Text,
        nullable=False,
        default=''
    )
    proposed_action = db.Column(
        PyIntEnum(AbstractAction),
        nullable=False
    )
    proposed_related_abstract_id = db.Column(
        db.Integer,
        db.ForeignKey('event_abstracts.abstracts.id'),
        index=True,
        nullable=True
    )
    proposed_contribution_type_id = db.Column(
        db.Integer,
        db.ForeignKey('events.contribution_types.id'),
        nullable=True,
        index=True
    )
    abstract = db.relationship(
        'Abstract',
        lazy=True,
        foreign_keys=abstract_id,
        backref=db.backref(
            'reviews',
            cascade='all, delete-orphan',
            lazy=True
        )
    )
    user = db.relationship(
        'User',
        lazy=True,
        backref=db.backref(
            'abstract_reviews',
            lazy='dynamic'
        )
    )
    track = db.relationship(
        'Track',
        lazy=True,
        foreign_keys=track_id,
        backref=db.backref(
            'abstract_reviews',
            lazy='dynamic'
        )
    )
    proposed_related_abstract = db.relationship(
        'Abstract',
        lazy=True,
        foreign_keys=proposed_related_abstract_id,
        backref=db.backref(
            'proposed_related_abstract_reviews',
            lazy='dynamic'
        )
    )
    proposed_tracks = db.relationship(
        'Track',
        secondary='event_abstracts.proposed_for_tracks',
        lazy=True,
        collection_class=set,
        backref=db.backref(
            'proposed_abstract_reviews',
            lazy='dynamic'
        )
    )
    proposed_contribution_type = db.relationship(
        'ContributionType',
        lazy=True,
        backref=db.backref(
            'abstract_reviews',
            lazy='dynamic'
        )
    )

    # relationship backrefs:
    # - ratings (AbstractReviewRating.review)

    @return_ascii
    def __repr__(self):
        return format_repr(self, 'id', 'abstract_id', 'user_id', proposed_action=None)

    @property
    def score(self):
        ratings = [r for r in self.ratings if not r.question.no_score]
        if not ratings:
            return None
        return sum(x.value for x in ratings) / len(ratings)
