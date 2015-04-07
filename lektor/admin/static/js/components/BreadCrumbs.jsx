'use strict';

var React = require('react');
var Router = require("react-router");
var {Link, RouteHandler} = Router;

var RecordComponent = require('./RecordComponent');
var utils = require('../utils');


class BreadCrumbs extends RecordComponent {

  constructor(props) {
    super(props);
    this.state = {
      recordPathInfo: null
    };
  }

  componentDidMount() {
    super();
    this.updateCrumbs();
  }

  componentWillReceiveProps(nextProps) {
    super(nextProps);
    this.updateCrumbs();
  }

  updateCrumbs() {
    var path = this.getRecordPath();
    if (path === null) {
      return;
    }

    utils.loadData('/pathinfo', {path: path})
      .then((resp) => {
        this.setState({
          recordPathInfo: {
            path: path,
            segments: resp.segments
          }
        });
      });
  }

  onCloseClick(e) {
    var segs = this.state.recordPathInfo.segments;
    if (segs.length > 0) {
      window.location.href = utils.getCanonicalUrl(segs[segs.length - 1].url_path);
      e.preventDefault();
    }
  }

  render() {
    var crumbs = [];
    var target = this.isRecordPreviewActive() ? 'preview' : 'edit';
    var lastItem = null;

    if (this.state.recordPathInfo != null) {
      crumbs = this.state.recordPathInfo.segments.map((item) => {
        var urlPath = utils.fsToUrlPath(item.path);
        var label = item.label;
        var className = 'record-crumb';

        if (!item.exists) {
          label = item.id;
          className += ' missing-record-crumb';
        }
        lastItem = item;

        return (
          <li key={item.path} className={className}>
            <Link to={target} params={{path: urlPath}}>{label}</Link>
          </li>
        );
      });
    }

    return (
      <div className="breadcrumbs">
        <ul className="breadcrumb container">
          {this.props.children}
          {crumbs}
          {lastItem && lastItem.can_have_children ? (
            <li className="new-record-crumb">
              <Link to="add-child" params={{path: utils.fsToUrlPath(
                lastItem.path)}}>+</Link>
            </li>
          ) : null}
          {' ' /* this space is needed for chrome ... */}
          <li className="close"><a href="/" onClick={
            this.onCloseClick.bind(this)}>Return to Website</a></li>
        </ul>
      </div>
    );
  }
}

module.exports = BreadCrumbs;
