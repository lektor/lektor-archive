'use strict';

var React = require('react');
var Router = require("react-router");
var {Link} = Router;

var RecordState = require('../mixins/RecordState');
var utils = require('../utils');
var hub = require('../hub');
var {AttachmentsChangedEvent} = require('../events');
var {gettext} = utils;
var RecordComponent = require('../components/RecordComponent');


class Sidebar extends RecordComponent {

  constructor() {
    this.state = this._getInitialState();
  }

  _getInitialState() {
    return {
      recordAttachments: [],
      recordChildren: [],
      canHaveAttachments: false,
      canHaveChildren: false,
      isAttachment: false,
      recordExists: false
    };
  }

  componentDidMount() {
    this._updateRecordInfo();

    hub.subscribe(AttachmentsChangedEvent, this.onAttachmentsChanged, this);
  }

  componentWillReceiveProps(nextProps) {
    this._updateRecordInfo();
  }

  componentWillUnmount() {
    hub.unsubscribe(AttachmentsChangedEvent, this.onAttachmentsChanged, this);
  }

  onAttachmentsChanged(event) {
    if (event.recordPath === this.getRecordPath()) {
      this._updateRecordInfo();
    }
  }

  _updateRecordInfo() {
    var path = this.getRecordPath();
    if (path === null) {
      this.setState(this._getInitialState());
      return;
    }

    utils.loadData('/recordinfo', {path: path})
      .then(function(resp) {
        this.setState({
          recordAttachments: resp.attachments,
          recordChildren: resp.children,
          canHaveAttachments: resp.can_have_attachments,
          canHaveChildren: resp.can_have_children,
          isAttachment: resp.is_attachment,
          recordExists: resp.exists
        });
      }.bind(this));
  }

  renderPageActions() {
    var urlPath = utils.fsToUrlPath(this.getRecordPath());
    var links = [];
    var linkParams = {path: urlPath};
    var deleteLink = null;

    links.push(
      <li key='edit'><Link to="edit" params={linkParams
        }>{gettext('Edit')}</Link></li>
    );

    if (urlPath !== 'root') {
      links.push(
        <li key='delete'><Link to="delete" params={
          linkParams}>{gettext('Delete')}</Link></li>
      );
    }

    links.push(
      <li key='preview'><Link to="preview" params={linkParams
        }>{gettext('Preview')}</Link></li>
    );

    if (this.state.canHaveChildren) {
      links.push(
        <li key='add-child'><Link to="add-child" params={linkParams
          }>{gettext('Add Child')}</Link></li>
      );
    }

    if (this.state.canHaveAttachments) {
      links.push(
        <li key='add-attachment'><Link to="add-attachment" params={linkParams
          }>{gettext('Add Attachment')}</Link></li>
      );
    }

    return (
      <div key="actions" className="section">
        <h3>{gettext('Actions')}</h3>
        <ul className="nav">
          {links}
          {deleteLink}
        </ul>
      </div>
    );
  }

  renderChildActions() {
    var target = this.isRecordPreviewActive() ? 'preview' : 'edit';

    var items = this.state.recordChildren.map(function(child) {
      var urlPath = utils.fsToUrlPath(child.path);
      return (
        <li key={child._id}>
          <Link to={target} params={{path: urlPath}}>{child.label}</Link>
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
  }

  renderAttachmentActions() {
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
  }

  render() {
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
}

module.exports = Sidebar;
