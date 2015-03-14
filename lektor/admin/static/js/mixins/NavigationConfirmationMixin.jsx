'use strict';

var React = require('react');
var utils = require('../utils');
var {gettext} = utils;


var unloadMessage = gettext('You have unsaved information, are you sure you want to leave this page?');

var NavigationConfirmationMixin = {
  statics: {
    willTransitionFrom: function(transition, component) {
      if (!component.hasPendingChanges || component.hasPendingChanges()) {
        if (!confirm(unloadMessage)) {
          transition.abort();
        }
      }
    }
  },

  componentDidMount: function() {
    window.addEventListener('beforeunload', this._beforeUnloadConfirmation);
  },

  componentWillUnmount: function() {
    window.removeEventListener('beforeunload', this._beforeUnloadConfirmation);
  },

  _beforeUnloadConfirmation: function(event) {
    if (!this.hasPendingChanges || this.hasPendingChanges()) {
      (event || window.event).returnValue = unloadMessage;
      return unloadMessage;
    }
  },
};

module.exports = NavigationConfirmationMixin;
