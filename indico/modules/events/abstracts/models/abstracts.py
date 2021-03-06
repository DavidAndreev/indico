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

from sqlalchemy.ext.declarative import declared_attr

from indico.core.db import db
from indico.core.db.sqlalchemy import PyIntEnum, UTCDateTime
from indico.core.db.sqlalchemy.descriptions import DescriptionMixin, RenderMode
from indico.core.db.sqlalchemy.util.models import auto_table_args
from indico.modules.events.abstracts.models.reviews import AbstractAction
from indico.modules.events.models.persons import AuthorsSpeakersMixin
from indico.modules.events.contributions.models.contributions import _get_next_friendly_id, CustomFieldsMixin
from indico.util.date_time import now_utc
from indico.util.i18n import _
from indico.util.locators import locator_property
from indico.util.string import format_repr, return_ascii, text_to_repr
from indico.util.struct.enum import TitledIntEnum


class AbstractState(TitledIntEnum):
    __titles__ = [None, _("Submitted"), _("Withdrawn"), _("Accepted"), _("Rejected"), _("Merged"), _("Duplicate")]
    submitted = 1
    withdrawn = 2
    accepted = 3
    rejected = 4
    merged = 5
    duplicate = 6


class AbstractPublicState(TitledIntEnum):
    __titles__ = {i: title for i, title in enumerate(AbstractState.__titles__[2:], 2)}
    __titles__.update({-1: _("Awaiting Review"), -2: _("Under Review")})
    # regular states (must match AbstractState!)
    withdrawn = 2
    accepted = 3
    rejected = 4
    merged = 5
    duplicate = 6
    # special states
    awaiting = -1
    under_review = -2


class AbstractReviewingState(TitledIntEnum):
    __titles__ = [_("Not Started"), _("In progress"), _("Positive"), _("Conflicting"), _("Negative"), _("Mixed")]
    not_started = 0
    in_progress = 1
    positive = 2
    conflicting = 3
    negative = 4
    mixed = 5


class Abstract(DescriptionMixin, CustomFieldsMixin, AuthorsSpeakersMixin, db.Model):
    """Represents an abstract that can be associated to a Contribution."""

    __tablename__ = 'abstracts'
    __auto_table_args = (db.UniqueConstraint('friendly_id', 'event_id'),
                         db.CheckConstraint('(state = {}) OR (accepted_track_id IS NULL)'
                                            .format(AbstractState.accepted),
                                            name='accepted_track_id_only_accepted'),
                         db.CheckConstraint('(state = {}) OR (accepted_contrib_type_id IS NULL)'
                                            .format(AbstractState.accepted),
                                            name='accepted_contrib_type_id_only_accepted'),
                         db.CheckConstraint('(state = {}) = (merged_into_id IS NOT NULL)'
                                            .format(AbstractState.merged),
                                            name='merged_into_id_only_merged'),
                         db.CheckConstraint('(state = {}) = (duplicate_of_id IS NOT NULL)'
                                            .format(AbstractState.duplicate),
                                            name='duplicate_of_id_only_duplicate'),
                         {'schema': 'event_abstracts'})

    possible_render_modes = {RenderMode.markdown}
    default_render_mode = RenderMode.markdown

    @declared_attr
    def __table_args__(cls):
        return auto_table_args(cls)

    id = db.Column(
        db.Integer,
        primary_key=True
    )
    #: The friendly ID for the abstract (same as the legacy id in ZODB)
    friendly_id = db.Column(
        db.Integer,
        nullable=False,
        default=_get_next_friendly_id
    )
    event_id = db.Column(
        db.Integer,
        db.ForeignKey('events.events.id'),
        index=True,
        nullable=False
    )
    title = db.Column(
        db.String,
        nullable=False
    )
    #: ID of the user who submitted the abstract
    submitter_id = db.Column(
        db.Integer,
        db.ForeignKey('users.users.id'),
        index=True,
        nullable=False
    )
    submitted_contrib_type_id = db.Column(
        db.Integer,
        db.ForeignKey('events.contribution_types.id'),
        nullable=True,
        index=True
    )
    submitted_dt = db.Column(
        UTCDateTime,
        nullable=False,
        default=now_utc
    )
    modified_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.users.id'),
        nullable=True,
        index=True
    )
    modified_dt = db.Column(
        UTCDateTime,
        nullable=True,
    )
    state = db.Column(
        PyIntEnum(AbstractState),
        nullable=False,
        default=AbstractState.submitted
    )
    submission_comment = db.Column(
        db.Text,
        nullable=False,
        default=''
    )
    #: ID of the user who judged the abstract
    judge_id = db.Column(
        db.Integer,
        db.ForeignKey('users.users.id'),
        index=True,
        nullable=True
    )
    judgment_comment = db.Column(
        db.Text,
        nullable=False,
        default=''
    )
    judgment_dt = db.Column(
        UTCDateTime,
        nullable=True,
    )
    accepted_track_id = db.Column(
        db.Integer,
        db.ForeignKey('events.tracks.id'),
        nullable=True,
        index=True
    )
    accepted_contrib_type_id = db.Column(
        db.Integer,
        db.ForeignKey('events.contribution_types.id'),
        nullable=True,
        index=True
    )
    merged_into_id = db.Column(
        db.Integer,
        db.ForeignKey('event_abstracts.abstracts.id'),
        index=True,
        nullable=True
    )
    duplicate_of_id = db.Column(
        db.Integer,
        db.ForeignKey('event_abstracts.abstracts.id'),
        index=True,
        nullable=True
    )
    is_deleted = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )
    event_new = db.relationship(
        'Event',
        lazy=True,
        backref=db.backref(
            'abstracts',
            primaryjoin='(Abstract.event_id == Event.id) & ~Abstract.is_deleted',
            cascade='all, delete-orphan',
            lazy=True
        )
    )
    #: User who submitted the abstract
    submitter = db.relationship(
        'User',
        lazy=True,
        foreign_keys=submitter_id,
        backref=db.backref(
            'abstracts',
            primaryjoin='(Abstract.submitter_id == User.id) & ~Abstract.is_deleted',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )
    modified_by = db.relationship(
        'User',
        lazy=True,
        foreign_keys=modified_by_id,
        backref=db.backref(
            'modified_abstracts',
            primaryjoin='(Abstract.modified_by_id == User.id) & ~Abstract.is_deleted',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )
    submitted_contrib_type = db.relationship(
        'ContributionType',
        lazy=True,
        foreign_keys=submitted_contrib_type_id,
        backref=db.backref(
            'proposed_abstracts',
            primaryjoin='(Abstract.submitted_contrib_type_id == ContributionType.id) & ~Abstract.is_deleted',
            lazy=True
        )
    )
    submitted_for_tracks = db.relationship(
        'Track',
        secondary='event_abstracts.submitted_for_tracks',
        collection_class=set,
        backref=db.backref(
            'abstracts_submitted',
            primaryjoin='event_abstracts.submitted_for_tracks.c.track_id == Track.id',
            secondaryjoin='(event_abstracts.submitted_for_tracks.c.abstract_id == Abstract.id) & ~Abstract.is_deleted',
            collection_class=set,
            lazy=True
        )
    )
    reviewed_for_tracks = db.relationship(
        'Track',
        secondary='event_abstracts.reviewed_for_tracks',
        collection_class=set,
        backref=db.backref(
            'abstracts_reviewed',
            primaryjoin='event_abstracts.reviewed_for_tracks.c.track_id == Track.id',
            secondaryjoin='(event_abstracts.reviewed_for_tracks.c.abstract_id == Abstract.id) & ~Abstract.is_deleted',
            collection_class=set,
            lazy=True
        )
    )
    #: User who judged the abstract
    judge = db.relationship(
        'User',
        lazy=True,
        foreign_keys=judge_id,
        backref=db.backref(
            'judged_abstracts',
            primaryjoin='(Abstract.judge_id == User.id) & ~Abstract.is_deleted',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )
    accepted_track = db.relationship(
        'Track',
        lazy=True,
        backref=db.backref(
            'abstracts_accepted',
            primaryjoin='(Abstract.accepted_track_id == Track.id) & ~Abstract.is_deleted',
            lazy=True
        )
    )
    accepted_contrib_type = db.relationship(
        'ContributionType',
        lazy=True,
        foreign_keys=accepted_contrib_type_id,
        backref=db.backref(
            'abstracts_accepted',
            primaryjoin='(Abstract.accepted_contrib_type_id == ContributionType.id) & ~Abstract.is_deleted',
            lazy=True
        )
    )
    merged_into = db.relationship(
        'Abstract',
        lazy=True,
        remote_side=id,
        foreign_keys=merged_into_id,
        backref=db.backref(
            'merged_abstracts',
            primaryjoin=(db.remote(merged_into_id) == id) & ~db.remote(is_deleted),
            lazy=True
        )
    )
    duplicate_of = db.relationship(
        'Abstract',
        lazy=True,
        remote_side=id,
        foreign_keys=duplicate_of_id,
        backref=db.backref(
            'duplicate_abstracts',
            primaryjoin=(db.remote(duplicate_of_id) == id) & ~db.remote(is_deleted),
            lazy=True
        )
    )
    #: Data stored in abstract/contribution fields
    field_values = db.relationship(
        'AbstractFieldValue',
        lazy=True,
        cascade='all, delete-orphan',
        backref=db.backref(
            'abstract',
            lazy=True
        )
    )
    #: Persons associated with this abstract
    person_links = db.relationship(
        'AbstractPersonLink',
        lazy=True,
        cascade='all, delete-orphan',
        backref=db.backref(
            'abstract',
            lazy=True
        )
    )

    # relationship backrefs:
    # - comments (AbstractComment.abstract)
    # - contribution (Contribution.abstract)
    # - duplicate_abstracts (Abstract.duplicate_of)
    # - email_logs (AbstractEmailLogEntry.abstract)
    # - files (AbstractFile.abstract)
    # - merged_abstracts (Abstract.merged_into)
    # - proposed_related_abstract_reviews (AbstractReview.proposed_related_abstract)
    # - reviews (AbstractReview.abstract)

    @property
    def public_state(self):
        if self.state != AbstractState.submitted:
            return getattr(AbstractPublicState, self.state.name)
        elif self.reviews:
            return AbstractPublicState.under_review
        else:
            return AbstractPublicState.awaiting

    @property
    def reviewing_state(self):
        if not self.reviews:
            return AbstractReviewingState.not_started
        track_reviews = {x: self.get_track_reviewing_state(x) for x in self.reviewed_for_tracks}
        if any(x == AbstractReviewingState.not_started for x in track_reviews.itervalues()):
            return AbstractReviewingState.in_progress
        elif all(x == AbstractReviewingState.negative for x in track_reviews.itervalues()):
            return AbstractReviewingState.negative
        elif all(x == AbstractReviewingState.positive for x in track_reviews.itervalues()):
            if len(self.reviewed_for_tracks) == 1:
                return AbstractReviewingState.positive
            else:
                return AbstractReviewingState.conflicting
        else:
            return AbstractReviewingState.mixed

    @property
    def score(self):
        scores = [x.score for x in self.reviews if x.score is not None]
        if not scores:
            return None
        return sum(scores) / len(scores)

    @property
    def data_by_field(self):
        return {value.contribution_field_id: value for value in self.field_values}

    @locator_property
    def locator(self):
        return dict(self.event_new.locator, abstract_id=self.id)

    @return_ascii
    def __repr__(self):
        return format_repr(self, 'id', 'event_id', is_deleted=False, _text=text_to_repr(self.title))

    def can_access(self, user):
        if not user:
            return False
        if self.submitter == user:
            return True
        if self.event_new.can_manage(user):
            return True
        if any(x.person.user == user for x in self.person_links):
            return True
        return self.can_review(user)

    def can_review(self, user):
        if not user:
            return False
        elif not self.event_new.can_manage(user, role='abstract_reviewer', explicit_role=True):
            return False
        else:
            # The total number of tracks a user is reviewing (indico-wide) is usually
            # reasonably low so we just access the relationship instead of sending a
            # more specific query which would need to be cached to avoid repeating it
            # when performing this check on many abstracts.
            tracks = {t for t in user.reviewer_for_tracks if t.event_new == self.event_new}
            return bool(tracks) and bool(tracks & self.reviewed_for_tracks)

    def can_edit(self, user):
        if not user:
            return False
        is_owner = user == self.submitter or any(x.person.user == user for x in self.person_links)
        is_manager = self.event_new.can_manage(user)
        if not is_owner and not is_manager:
            return False
        elif self.public_state == AbstractPublicState.awaiting:
            return True
        elif self.public_state == AbstractPublicState.under_review and is_manager:
            return True
        elif self.public_state == AbstractPublicState.withdrawn and is_manager:
            return True
        else:
            return False

    def get_track_reviewing_state(self, track):
        if track not in self.reviewed_for_tracks:
            raise ValueError("Abstract not in review for given track")
        reviews = self.get_track_reviews(track)
        if not reviews:
            return AbstractReviewingState.not_started
        rejections = any(x.proposed_action == AbstractAction.reject for x in reviews)
        acceptances = any(x.proposed_action == AbstractAction.accept for x in reviews)
        if acceptances and not rejections:
            return AbstractReviewingState.positive
        elif rejections and not acceptances:
            return AbstractReviewingState.negative
        else:
            return AbstractReviewingState.mixed

    def get_track_reviews(self, track):
        return [x for x in self.reviews if x.track == track]

    def get_track_score(self, track):
        if track not in self.reviewed_for_tracks:
            raise ValueError("Abstract not in review for given track")
        reviews = [x for x in self.reviews if x.track == track]
        scores = [x.score for x in reviews if x.score is not None]
        if not scores:
            return None
        return sum(scores) / len(scores)
