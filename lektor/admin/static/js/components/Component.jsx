'use strict';

var React = require('react');
var dialogSystem = require('../dialogSystem');


class Component extends React.Component {

  componentDidMount() {
  }

  componentWillUnmount() {
  }

  componentDidUpdate() {
  }

  componentWillReceiveProps(nextProps) {
  }
}

Component.willTransitionFrom = (transition, component) => {
  if (dialogSystem.preventNavigation()) {
    transition.abort();
  } else {
    dialogSystem.dismissDialog();
  }
}


module.exports = Component;
