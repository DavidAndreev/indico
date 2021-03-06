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

from flask import request

from indico.core.db import db
from indico.modules.events.abstracts.controllers.management import RHManageAbstractsBase
from indico.modules.events.abstracts.forms import (EditEmailTemplateRuleForm, EditEmailTemplateTextForm,
                                                   CreateEmailTemplateForm)
from indico.modules.events.abstracts.models.email_templates import AbstractEmailTemplate
from indico.modules.events.abstracts.notifications import get_abstract_notification_tpl_module
from indico.modules.events.abstracts.util import build_default_email_template, create_mock_abstract
from indico.web.flask.templating import get_template_module
from indico.web.util import jsonify_data, jsonify_template


class RHEmailTemplateList(RHManageAbstractsBase):
    """Display list of e-mail templates."""

    def _process(self):
        return jsonify_template('events/abstracts/management/notification_tpl_list.html', event=self.event_new)


class RHAddEmailTemplate(RHManageAbstractsBase):
    """Add a new e-mail template."""

    def _process(self):
        form = CreateEmailTemplateForm(event=self.event_new)
        if form.validate_on_submit():
            new_tpl = build_default_email_template(self.event_new, form.default_tpl.data)
            form.populate_obj(new_tpl)
            self.event_new.abstract_email_templates.append(new_tpl)
            db.session.flush()

            tpl = get_template_module('events/abstracts/management/_notification_tpl_list.html')
            return jsonify_data(html=tpl.render_notification_list(self.event_new))
        return jsonify_template('events/abstracts/management/notification_tpl_form.html', form=form)


class RHEditEmailTemplateBase(RHManageAbstractsBase):
    """Base class for operations that involve editing an e-mail template."""

    normalize_url_spec = {
        'locators': {
            lambda self: self.email_tpl
        }
    }

    def _checkParams(self, params):
        RHManageAbstractsBase._checkParams(self, params)
        self.email_tpl = AbstractEmailTemplate.get_one(request.view_args['email_tpl_id'])


class RHEditEmailTemplateRules(RHEditEmailTemplateBase):
    """Edit the rules of a notification template."""

    def _process(self):
        form = EditEmailTemplateRuleForm(obj=self.email_tpl, event=self.event_new)
        if form.validate_on_submit():
            form.populate_obj(self.email_tpl)
            tpl = get_template_module('events/abstracts/management/_notification_tpl_list.html')
            return jsonify_data(html=tpl.render_notification_list(self.event_new))
        return jsonify_template('events/abstracts/management/notification_tpl_form.html',
                                form=form, is_edit=True)


class RHEditEmailTemplateText(RHEditEmailTemplateBase):
    """Edit the e-mail text of a notification template."""

    def _process(self):
        form = EditEmailTemplateTextForm(obj=self.email_tpl, event=self.event_new)
        if form.validate_on_submit():
            form.populate_obj(self.email_tpl)
            tpl = get_template_module('events/abstracts/management/_notification_tpl_list.html')
            return jsonify_data(html=tpl.render_notification_list(self.event_new))
        return jsonify_template('events/abstracts/management/notification_tpl_text_form.html', form=form, is_edit=True)


class RHSortEmailTemplates(RHManageAbstractsBase):
    """Sort e-mail templates according to the order provided by the client."""

    def _process(self):
        sort_order = request.json['sort_order']
        tpls = {s.id: s for s in self.event_new.abstract_email_templates}
        for position, tpl_id in enumerate(sort_order, 1):
            if tpl_id in tpls:
                tpls[tpl_id].position = position


class RHDeleteEmailTemplate(RHEditEmailTemplateBase):
    """Delete an e-mail template."""

    def _process(self):
        db.session.delete(self.email_tpl)
        tpl = get_template_module('events/abstracts/management/_notification_tpl_list.html')
        return jsonify_data(html=tpl.render_notification_list(self.event_new), flash=False)


class RHPreviewEmailTemplate(RHEditEmailTemplateBase):
    """Preview an e-mail template."""

    def _process(self):
        self.commit = False
        abstract = create_mock_abstract(self.event_new)
        tpl = get_abstract_notification_tpl_module(self.email_tpl, abstract)
        return jsonify_template('events/abstracts/management/notification_preview.html',
                                subject=tpl.get_subject(), body=tpl.get_body())
