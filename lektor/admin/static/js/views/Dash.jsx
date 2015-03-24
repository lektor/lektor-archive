'use strict';

var React = require('react');

var Dash = React.createClass({
  contextTypes: {
    router: React.PropTypes.any.isRequired
  },

  componentDidMount: function() {
    return this.context.router.transitionTo('preview', {'path': 'root'});
  },

  render: function() {
    return null;
  }
});

module.exports = Dash;
