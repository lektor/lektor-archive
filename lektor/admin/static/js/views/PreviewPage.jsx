'use strict';

var React = require('react');
var Router = require('react-router');

var utils = require('../utils');
var RecordState = require('../mixins/RecordState');

var PreviewPage = React.createClass({
  mixins: [
    RecordState
  ],

  getInitialState: function() {
    return {
      pageUrl: null
    }
  },

  componentWillReceiveProps: function() {
    this.syncState();
  },

  componentDidMount: function() {
    this.syncState();
  },

  syncState: function() {
    var path = this.getRecordPath();
    if (path === null) {
      this.setState(this.getInitialState());
      return;
    }

    utils.loadData('/previewinfo', {path: path})
      .then(function(resp) {
        this.setState({
          pageUrl: resp.url
        });
      }.bind(this));
  },

  componentDidUpdate: function() {
    var frame = this.refs.iframe.getDOMNode();
    var intendedPath = this.getRecordPath();
    var framePath = this.getFramePath();

    if (!utils.urlPathsConsideredEqual(intendedPath, framePath)) {
      frame.src = utils.getCanonicalUrl(intendedPath);
    }

    frame.onload = function(event) {
      this.onFrameNavigated();
    }.bind(this);
  },

  getFramePath: function() {
    var frame = this.refs.iframe.getDOMNode();
    return utils.fsPathFromAdminObservedPath(
      frame.contentWindow.location.pathname);
  },

  onFrameNavigated: function() {
    var fsPath = this.getFramePath();
    if (fsPath === null) {
      return;
    }
    utils.loadData('/matchurl', {url_path: fsPath})
      .then(function(resp) {
        if (resp.exists) {
          var urlPath = utils.fsToUrlPath(resp.path);
          this.context.router.transitionTo('preview', {path: urlPath});
        }
      }.bind(this));
  },

  render: function() {
    return (
      <div className="preview">
        <iframe ref="iframe"></iframe>
      </div>
    );
  }
});

module.exports = PreviewPage;
