'use strict';

var React = require('react');
var Router = require("react-router");
var {Link, RouteHandler} = Router;

var RecordState = require('../mixins/RecordState');
var utils = require('../utils');


var BreadCrumbs = React.createClass({
  mixins: [RecordState],

  getInitialState: function() {
    return {
      recordPathInfo: null
    }
  },

  componentDidMount: function() {
    this.updateCrumbs();
  },

  componentWillReceiveProps: function(nextProps) {
    this.updateCrumbs();
  },

  updateCrumbs: function() {
    var path = this.getRecordPath();
    if (path === null) {
      return;
    }

    utils.loadData('/pathinfo', {path: path})
      .then(function(resp) {
        this.setState({
          recordPathInfo: {
            path: path,
            segments: resp.segments
          }
        });
      }.bind(this));
  },

  onCloseClick: function(e) {
    var segs = this.state.recordPathInfo.segments;
    if (segs.length > 0) {
      window.location.href = utils.getCanonicalUrl(segs[segs.length - 1].url_path);
      e.preventDefault();
    }
  },

  render: function() {
    var crumbs = [];
    var target = this.isRecordPreviewActive() ? 'preview' : 'edit';

    if (this.state.recordPathInfo != null) {
      crumbs = this.state.recordPathInfo.segments.map(function(item) {
        var urlPath = utils.fsToUrlPath(item.path);
        var label = item.label;
        var className = 'record-crumb';

        if (!item.exists) {
          label = item.id;
          className += ' missing-record-crumb';
        }

        return (
          <li key={item.path} className={className}>
            <Link to={target} params={{path: urlPath}}>{label}</Link>
          </li>
        );
      });
    }
    return (
      <div className="breadcrumbs">
        <ul className="breadcrumb">
          {crumbs}
          <li className="close"><a href="/" onClick={this.onCloseClick
            }>Return to Website</a></li>
        </ul>
      </div>
    );
  }
});

module.exports = BreadCrumbs;
