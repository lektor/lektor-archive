'use strict';

var React = require('react');
var Router = require("react-router");
var {Link} = Router;

var RecordState = require('../mixins/RecordState');
var utils = require('../utils');
var {gettext} = utils;


var Sidebar = React.createClass({
  mixins: [RecordState],

  getInitialState: function() {
    return {
      recordAttachments: [],
      recordChildren: [],
      canHaveAttachments: false,
      canHaveChildren: false,
      isAttachment: false
    };
  },

  componentDidMount: function() {
    this._updateRecordInfo();
  },

  componentWillReceiveProps: function(nextProps) {
    this._updateRecordInfo();
  },

  _updateRecordInfo: function() {
    var path = this.getRecordPath();
    if (path === null) {
      this.setState(this.getInitialState());
      return;
    }

    utils.loadData('/recordinfo', {path: path})
      .then(function(resp) {
        this.setState({
          recordAttachments: resp.attachments,
          recordChildren: resp.children,
          canHaveAttachments: resp.can_have_attachments,
          canHaveChildren: resp.can_have_children,
          isAttachment: resp.is_attachment
        });
      }.bind(this));
  },

  renderPageActions: function() {
    var urlPath = utils.fsToUrlPath(this.getRecordPath());
    var linkParams = {path: urlPath};
    return (
      <div key="actions" className="section">
        <h3>{gettext('Actions')}</h3>
        <ul className="nav">
          <li><Link to="edit" params={linkParams}>{gettext('Edit')}</Link></li>
          <li><Link to="delete" params={linkParams}>{gettext('Delete')}</Link></li>
          <li><Link to="preview" params={linkParams}>{gettext('Preview')}</Link></li>
        </ul>
      </div>
    );
  },

  renderChildActions: function() {
    var items = this.state.recordChildren.map(function(child) {
      var urlPath = utils.fsToUrlPath(child.path);
      return (
        <li key={child._id}>
          <Link to="edit" params={{path: urlPath}}>{child.label}</Link>
        </li>
      )
    });
    return (
      <div key="children" className="section">
        <h3>{gettext('Children')}</h3>
        <ul className="nav record-children">
          {items}
        </ul>
      </div>
    );
  },

  renderAttachmentActions: function() {
    var items = this.state.recordAttachments.map(function(atch) {
      var urlPath = utils.fsToUrlPath(atch.path);
      return (
        <li key={atch._id}>
          <Link to="edit" params={{path: urlPath}}>{atch._id} ({atch.type})</Link>
        </li>
      )
    });
    return (
      <div key="attachments" className="section">
        <h3>{gettext('Attachments')}</h3>
        <ul className="nav record-attachments">
          {items}
        </ul>
      </div>
    );
  },

  render: function() {
    var sections = [];

    if (this.getRecordPath() !== null) {
      sections.push(this.renderPageActions());
    }

    if (this.state.canHaveChildren) {
      sections.push(this.renderChildActions());
    }

    if (this.state.canHaveAttachments) {
      sections.push(this.renderAttachmentActions());
    }

    return <div>{sections}</div>;
  }
});

module.exports = Sidebar;
