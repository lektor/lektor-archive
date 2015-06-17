'use strict';

var qs = require('querystring');
var React = require('react');
var Router = require('react-router');

var RecordComponent = require('../components/RecordEditComponent');
var utils = require('../utils');
var i18n = require('../i18n');
var hub = require('../hub');
var {AttachmentsChangedEvent} = require('../events');


class DeletePage extends RecordComponent {

  constructor(props) {
    super(props);

    this.state = {
      recordInfo: null
    };
  }

  componentDidMount() {
    super();
    this.syncDialog();
  }

  componentWillReceiveProps(nextProps) {
    super(nextProps);
    this.syncDialog();
  }

  syncDialog() {
    utils.loadData('/deleterecord', {path: this.getRecordPath()})
      .then((resp) => {
        this.setState({
          recordInfo: resp.record_info
        });
      });
  }

  deleteRecord(event) {
    var path = this.getRecordPath();
    var parent = utils.getParentFsPath(path);
    var targetPath;
    if (parent === null) {
      targetPath = 'root';
    } else {
      targetPath = utils.fsToUrlPath(parent);
    }

    utils.apiRequest('/deleterecord', {data: {path: path}, method: 'POST'})
      .then((resp) => {
        if (this.state.recordInfo.is_attachment) {
          hub.emit(new AttachmentsChangedEvent({
            recordPath: this.getParentRecordPath(),
            attachmentsRemoved: [this.state.recordInfo.id]
          }));
        }
        this.context.router.transitionTo('edit', {path: targetPath});
      });
  }

  cancelDelete(event) {
    var urlPath = utils.fsToUrlPath(this.getRecordPath());
    this.context.router.transitionTo('edit', {path: urlPath});
  }

  render() {
    var ri = this.state.recordInfo;

    if (!ri || !ri.can_be_deleted) {
      return null;
    }

    var elements = [];
    var children = [];
    var attachments = [];

    if (ri.is_attachment) {
      elements.push(
        <p key="attachment">
          {i18n.trans('DELETE_ATTACHMENT_PROMPT')}
        </p>
      );
    } else {
      elements.push(
        <p key="child-info">
          {i18n.trans('DELETE_PAGE_PROMPT')}
        </p>
      );
      if (ri.child_count > 0) {
        elements.push(
          <p key="page">
            {i18n.trans('DELETE_PAGE_CHILDREN_WARNING')}
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
        <h2>{i18n.trans('DELETE_RECORD').replace('%s', this.state.recordInfo.label)}</h2>
        {elements}
        <div style={{display: children.length > 0 ? 'block' : 'none'}}>
          <h4>{i18n.trans('CHILD_PAGES_TO_BE_DELETED')}</h4>
          <ul>
            {children}
          </ul>
        </div>
        <div style={{display: attachments.length > 0 ? 'block' : 'none'}}>
          <h4>{i18n.trans('ATTACHMENTS_TO_BE_DELETED')}</h4>
          <ul>
            {attachments}
          </ul>
        </div>
        <div className="actions">
          <button className="btn btn-primary"
            onClick={this.deleteRecord.bind(this)}>{i18n.trans('YES_DELETE')}</button>
          <button className="btn btn-default"
            onClick={this.cancelDelete.bind(this)}>{i18n.trans('NO_CANCEL')}</button>
        </div>
      </div>
    );
  }
}

module.exports = DeletePage;
