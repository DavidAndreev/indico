/* This file is part of Indico.
 * Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
 *
 * Indico is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 3 of the
 * License, or (at your option) any later version.
 *
 * Indico is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Indico; if not, see <http://www.gnu.org/licenses/>.
 */

/* global setupListGenerator:false */

(function(global) {
    'use strict';

    global.setupAbstractList = function setupAbstractList() {
        var abstractListContainer = $('#abstract-list');

        var filterConfig = {
            itemHandle: 'tr',
            listItems: '#abstract-list tbody tr',
            term: '#search-input',
            state: '#filtering-state',
            placeholder: '#filter-placeholder'
        };

        abstractListContainer.on('indico:htmlUpdated', function() {
            abstractListContainer.find('.js-mathjax').mathJax();
        });

        setupListGenerator(filterConfig);
    };
})(window);
