'use strict';

var qs = require('querystring');
var React = require('react');
var Router = require('react-router');

var RecordState = require('../mixins/RecordState');
var utils = require('../utils');
var hub = require('../hub');
var {AttachmentsChangedEvent} = require('../events');
var {gettext, ngettext} = utils;


var DeletePage = React.createClass({
  mixins: [
    RecordState
  ],

  getInitialState: function() {
    return {
      recordInfo: null
    }
  },

  componentDidMount: function() {
    this.syncDialog();
  },

  componentWillReceiveProps: function(nextProps) {
    this.syncDialog();
  },

  syncDialog: function() {
    utils.loadData('/deleterecord', {path: this.getRecordPath()})
      .then(function(resp) {
        this.setState({
          recordInfo: resp.record_info
        });
      }.bind(this));
  },

  deleteRecord: function(event) {
    var path = this.getRecordPath();
    var parent = utils.getParentFsPath(path);
    var targetPath;
    if (parent === null) {
      targetPath = 'root';
    } else {
      targetPath = utils.fsToUrlPath(parent);
    }

    utils.apiRequest('/deleterecord', {data: {path: path}, method: 'POST'})
      .then(function(resp) {
        if (this.state.recordInfo.is_attachment) {
          hub.emit(new AttachmentsChangedEvent({
            recordPath: this.getParentRecordPath(),
            attachmentsRemoved: [this.state.recordInfo.id]
          }));
        }
        this.context.router.transitionTo('edit', {path: targetPath});
      }.bind(this));
  },

  cancelDelete: function(event) {
    var urlPath = utils.fsToUrlPath(this.getRecordPath());
    this.context.router.transitionTo('edit', {path: urlPath});
  },

  render: function() {
    var ri = this.state.recordInfo;

    if (!ri) {
      return null;
    }

    var elements = [];
    var children = [];
    var attachments = [];

    if (ri.is_attachment) {
      elements.push(
        <p key="attachment">
          {gettext('Do you really want to delete this attachment?')}
        </p>
      );
    } else {
      elements.push(
        <p key="child-info">
          {gettext('Do you really want to delete this page and all ' +
                   'of its attachments?')}
        </p>
      );
      if (ri.child_count > 0) {
        elements.push(
          <p key="page">
            {ngettext('This will also delete its %d child.',
                      'This will also delete its %d children.',
                      ri.child_count).replace('%d', ri.child_count)}
          </p>
        );

        children = ri.children.map(function(child) {
          return (
            <li key={child.id}>{child.label}</li>
          );
        });
        if (ri.child_count > children.length) {
          children.push(<li key='...'>...</li>);
        }
      }

      attachments = ri.attachments.map(function(atch) {
        return (
          <li key={atch.id}>{atch.id} ({atch.type})</li>
        );
      });
    }
    
    return (
      <div>
        <h2>{gettext('Delete “%s”').replace('%s', this.state.recordInfo.label)}</h2>
        {elements}
        <div style={{display: children.length > 0 ? 'block' : 'none'}}>
          <h4>{gettext('Children to be deleted:')}</h4>
          <ul>
            {children}
          </ul>
        </div>
        <div style={{display: attachments.length > 0 ? 'block' : 'none'}}>
          <h4>{gettext('Attachments to be deleted:')}</h4>
          <ul>
            {attachments}
          </ul>
        </div>
        <div className="actions">
          <button className="btn btn-primary"
            onClick={this.deleteRecord}>{gettext('Yes, delete')}</button>
          <button className="btn btn-default"
            onClick={this.cancelDelete}>{gettext('No, cancel')}</button>
        </div>
      </div>
    );
  }
});

module.exports = DeletePage;
