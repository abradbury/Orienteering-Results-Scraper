"use strict";

var Dispatcher = require('../dispatcher/appDispatcher');
var ActionTypes = require('../constants/actionTypes');
var EventEmitter = require('events').EventEmitter;
var assign = require('object-assign');  // Available natively on ES6
var _ = require('lodash');
var CHANGE_EVENT = 'change';

var _authors = [];   // prefixed with _ to indicate private

// Using object assign to take an empty, new object then extend this to
// utilise EventEmitter.prototype and finally add the rest of the store
var AuthorStore = assign({}, EventEmitter.prototype, {
    // Used by React components that would like to know when the store changes
    addChangeListener: function (callback) {
        this.on(CHANGE_EVENT, callback);
    },

    removeChangeListener: function (callback) {
        this.removeListener(CHANGE_EVENT, callback);
    },

    emitChange: function () {
        this.emit(CHANGE_EVENT);
    },

    getAllAuthors: function () {
        return _authors;
    },

    getAuthorById: function (id) {
        return _.find(_authors, { id: id });
    }
});

// This is private, hence, not exported
Dispatcher.register(function (action) {
    // Called when *any* action is dispatched
    switch (action.actionType) {
        case ActionTypes.CREATE_AUTHOR:
            _authors.push(action.author);
            AuthorStore.emitChange();
            break;

        case ActionTypes.INITIALISE:
            _authors = action.initialData.authors;
            AuthorStore.emitChange();
            break;

        case ActionTypes.UPDATE_AUTHOR:
            var existingAuthor = _.find(_authors, { id: action.author.id });
            var existingAuthorIndex = _.indexOf(_authors, existingAuthor);

            _authors.splice(existingAuthorIndex, 1, action.author);
            AuthorStore.emitChange();
            break;

        case ActionTypes.DELETE_AUTHOR:
            _.remove(_authors, function (author) {
                return action.id === author.id;
            });
            AuthorStore.emitChange();
            break;

        default:
        // no op (for all actions this store isn't interested in)
    }
});

module.exports = AuthorStore;