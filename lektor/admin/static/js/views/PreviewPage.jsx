'use strict';

var React = require('react');
var Router = require('react-router');

var utils = require('../utils');
var RecordComponent = require('../components/RecordComponent');


class PreviewPage extends RecordComponent {

  constructor(props) {
    super(props);
    this.state = {
      pageUrl: null,
      pageUrlFor: null
    };
  }

  componentWillReceiveProps(nextProps) {
    super(nextProps);
    this.syncState();
  }

  componentDidMount() {
    super();
    this.syncState();
  }

  syncState() {
    var path = this.getRecordPath();
    if (path === null) {
      this.setState(this.getInitialState());
      return;
    }

    utils.loadData('/previewinfo', {path: path})
      .then((resp) => {
        this.setState({
          pageUrl: resp.url,
          pageUrlFor: path
        });
      });
  }

  getIntendedPath() {
    if (this.state.pageUrlFor == this.getRecordPath()) {
      return this.state.pageUrl;
    }
    return null;
  }

  componentDidUpdate() {
    var frame = React.findDOMNode(this.refs.iframe);
    var intendedPath = this.getIntendedPath();
    if (intendedPath !== null) {
      var framePath = this.getFramePath();

      if (!utils.urlPathsConsideredEqual(intendedPath, framePath)) {
        frame.src = utils.getCanonicalUrl(intendedPath);
      }

      frame.onload = (event) => {
        this.onFrameNavigated();
      };
    }
  }

  getFramePath() {
    var frame = React.findDOMNode(this.refs.iframe);
    return utils.fsPathFromAdminObservedPath(
      frame.contentWindow.location.pathname);
  }

  onFrameNavigated() {
    var fsPath = this.getFramePath();
    if (fsPath === null) {
      return;
    }
    utils.loadData('/matchurl', {url_path: fsPath})
      .then((resp) => {
        if (resp.exists) {
          var urlPath = utils.fsToUrlPath(resp.path);
          this.context.router.transitionTo('preview', {path: urlPath});
        }
      });
  }

  render() {
    return (
      <div className="preview">
        <iframe ref="iframe"></iframe>
      </div>
    );
  }
}

module.exports = PreviewPage;
