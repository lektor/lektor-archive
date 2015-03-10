'use strict';

var qs = require('querystring');
var React = require('react');
var Router = require('react-router');

var utils = require('../utils');
var RecordState = require('../mixins/RecordState');

var PreviewPage = React.createClass({
  mixins: [
    RecordState,
    Router.Navigation
  ],

  getInitialState: function() {
    return {
      pageUrl: null
    }
  },

  componentWillReceiveProps: function() {
    this._syncState();
  },

  componentDidMount: function() {
    this._syncState();
  },

  _syncState: function() {
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
          this.transitionTo('preview', {path: urlPath});
        }
      }.bind(this));
  },

  navigateFrameIfNecessary: function() {
    var intendedPath = this.getRecordPath();
    var framePath = this.getFramePath();

    if (!utils.urlPathsConsideredEqual(intendedPath, framePath)) {
      this._syncState();
    }
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
