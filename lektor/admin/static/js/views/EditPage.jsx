'use strict';

var qs = require('querystring');
var React = require('react');
var Router = require('react-router');

var RecordState = require('../mixins/RecordState');

var EditPage = React.createClass({
  mixins: [
    RecordState
  ],
  render: function() {
    var path = this.getRecordPath();
    return <div>Edit Page {path}!</div>;
  }
});

module.exports = EditPage;
