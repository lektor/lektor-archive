'use strict';

var RecordComponent = require('./RecordComponent');
var utils = require('../utils');
var {gettext} = utils;


var unloadMessage = gettext('You have unsaved information, ' +
  'are you sure you want to leave this page?');


class RecordEditComponent extends RecordComponent {

  constructor() {
    super();

    this._beforeUnloadConfirmation = this._beforeUnloadConfirmation.bind(this);
  }

  componentDidMount() {
    super();
    window.addEventListener('beforeunload', this._beforeUnloadConfirmation);
  }

  componentWillUnmount() {
    window.removeEventListener('beforeunload', this._beforeUnloadConfirmation);
    super();
  }

  hasPendingChanges() {
    return false;
  }

  _beforeUnloadConfirmation(event) {
    if (this.hasPendingChanges()) {
      (event || window.event).returnValue = unloadMessage;
      return unloadMessage;
    }
  }
}

RecordEditComponent.willTransitionFrom = function(transition, component) {
  if (component.hasPendingChanges()) {
    if (!confirm(unloadMessage)) {
      transition.abort();
    }
  }
};


module.exports = RecordEditComponent;
