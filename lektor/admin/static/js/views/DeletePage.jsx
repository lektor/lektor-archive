'use strict';

var qs = require('querystring');
var React = require('react');
var Router = require('react-router');

var RecordState = require('../mixins/RecordState');

var DeletePage = React.createClass({
  mixins: [
    RecordState
  ],
  render: function() {
    var path = this.getRecordPath();
    return <div>Delete Page {path}!</div>;
  }
});

module.exports = DeletePage;
