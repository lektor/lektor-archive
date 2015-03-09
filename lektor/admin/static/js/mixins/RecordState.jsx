var React = require('react');
var Router = require('react-router');

var utils = require('../utils');

// XXX: this will all change in the new react router :(


var RecordStateMixin = {
  contextTypes: {
    getCurrentParams: React.PropTypes.func.isRequired
  },

  /* this returns the current record path segments as array */
  getRecordPathSegments: function() {
    return utils.urlPathToSegments(this.context.getCurrentParams().path);
  },

  /* this returns the path of the current record.  If the current page does
   * not have a path component then null is returned. */
  getRecordPath: function() {
    return utils.urlToFsPath(this.context.getCurrentParams().path);
  },

  /* returns the breadcrumbs for the current record path */
  getRecordCrumbs: function() {
    var segments = this.getRecordPathSegments();
    if (segments === null) {
      return [];
    }

    segments.unshift('root');

    var rv = [];
    for (var i = 0; i < segments.length; i++) {
      var curpath = segments.slice(0, i + 1).join(':');
      rv.push({
        id: 'path:' + curpath,
        urlPath: curpath,
        segments: segments.slice(1, i + 1),
        title: segments[i]
      });
    }

    return rv;
  }
};

module.exports = RecordStateMixin;
