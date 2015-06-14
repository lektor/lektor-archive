'use strict';

var RecordComponent = require('./RecordComponent');
var i18n = require('../i18n');


class RecordEditComponent extends RecordComponent {

  constructor(props) {
    super(props);

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
      var unloadMessage = i18n.trans('UNLOAD_ACTIVE_TAB');
      (event || window.event).returnValue = unloadMessage;
      return unloadMessage;
    }
  }
}

RecordEditComponent.willTransitionFrom = function(transition, component) {
  if (component.hasPendingChanges()) {
    var unloadMessage = i18n.trans('UNLOAD_ACTIVE_TAB');
    if (!confirm(unloadMessage)) {
      transition.abort();
    }
  }
};


module.exports = RecordEditComponent;
