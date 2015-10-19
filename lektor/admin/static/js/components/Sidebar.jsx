'use strict';

var React = require('react');
var Router = require("react-router");
var {Link} = Router;

var utils = require('../utils');
var i18n = require('../i18n');
var hub = require('../hub');
var {AttachmentsChangedEvent} = require('../events');
var RecordComponent = require('./RecordComponent');


class Sidebar extends RecordComponent {

  constructor(props) {
    super(props);

    this.state = this._getInitialState();
    this.onAttachmentsChanged = this.onAttachmentsChanged.bind(this);
  }

  _getInitialState() {
    return {
      recordAttachments: [],
      recordChildren: [],
      recordAlts: [],
      canHaveAttachments: false,
      canHaveChildren: false,
      isAttachment: false,
      canBeDeleted: false,
      recordExists: false
    };
  }

  componentDidMount() {
    this._updateRecordInfo();

    hub.subscribe(AttachmentsChangedEvent, this.onAttachmentsChanged);
  }

  componentWillReceiveProps(nextProps) {
    this._updateRecordInfo();
  }

  componentWillUnmount() {
    hub.unsubscribe(AttachmentsChangedEvent, this.onAttachmentsChanged);
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
      .then((resp) => {
        this.setState({
          recordAttachments: resp.attachments,
          recordChildren: resp.children,
          recordAlts: resp.alts,
          canHaveAttachments: resp.can_have_attachments,
          canHaveChildren: resp.can_have_children,
          isAttachment: resp.is_attachment,
          canBeDeleted: resp.can_be_deleted,
          recordExists: resp.exists
        });
      });
  }

  renderPageActions() {
    var urlPath = this.getUrlRecordPathWithAlt();
    var links = [];
    var linkParams = {path: urlPath};
    var deleteLink = null;

    links.push(
      <li key='edit'><Link to="edit" params={linkParams
        }>{this.state.isAttachment ?
          i18n.trans('EDIT_METADATA') :
          i18n.trans('EDIT')}</Link></li>
    );

    if (this.state.canBeDeleted) {
      links.push(
        <li key='delete'><Link to="delete" params={
          linkParams}>{i18n.trans('DELETE')}</Link></li>
      );
    }

    links.push(
      <li key='preview'><Link to="preview" params={linkParams
        }>{i18n.trans('PREVIEW')}</Link></li>
    );

    if (this.state.canHaveChildren) {
      links.push(
        <li key='add-child'><Link to="add-child" params={linkParams
          }>{i18n.trans('ADD_CHILD_PAGE')}</Link></li>
      );
    }

    if (this.state.canHaveAttachments) {
      links.push(
        <li key='add-attachment'><Link to="add-attachment" params={linkParams
          }>{i18n.trans('ADD_ATTACHMENT')}</Link></li>
      );
    }

    var title = this.state.isAttachment
      ? i18n.trans('ATTACHMENT_ACTIONS')
      : i18n.trans('PAGE_ACTIONS');

    return (
      <div key="actions" className="section">
        <h3>{title}</h3>
        <ul className="nav">
          {links}
          {deleteLink}
        </ul>
      </div>
    );
  }

  renderAlts() {
    if (this.state.recordAlts.length < 2) {
      return null;
    }

    var alt = this.getRecordAlt();

    var items = this.state.recordAlts.map((item) => {
      var title = i18n.trans(item.name_i18n);
      var className = 'alt';
      if (item.is_primary) {
        title += ' (' + i18n.trans('PRIMARY_ALT') + ')';
      } else if (item.primary_overlay) {
        title += ' (' + i18n.trans('PRIMARY_OVERLAY') + ')';
      }
      if (!item.exists) {
        className += ' alt-missing';
      }
      return (
        <li key={item.alt} className={className}><Link to="edit" params={
          {path: this.getUrlRecordPathWithAlt(null, item.alt)}
        }>{title}</Link></li>
      );
    });

    return (
      <div key="alts" className="section">
        <h3>{i18n.trans('ALTS')}</h3>
        <ul className="nav">
          {items}
        </ul>
      </div>
    );
  }

  renderChildActions() {
    var target = this.isRecordPreviewActive() ? 'preview' : 'edit';

    var items = this.state.recordChildren.map((child) => {
      var urlPath = this.getUrlRecordPathWithAlt(child.path);
      return (
        <li key={child['_id']}>
          <Link to={target} params={{path: urlPath}}>{child.label}</Link>
        </li>
      )
    });

    if (items.length == 0) {
      items.push(
        <li key="_missing">
          <em>{i18n.trans('NO_CHILD_PAGES')}</em>
        </li>
      );
    }

    return (
      <div key="children" className="section">
        <h3>{i18n.trans('CHILD_PAGES')}</h3>
        <ul className="nav record-children">
          {items}
        </ul>
      </div>
    );
  }

  renderAttachmentActions() {
    var items = this.state.recordAttachments.map((atch) => {
      var urlPath = this.getUrlRecordPathWithAlt(atch.path);
      return (
        <li key={atch['_id']}>
          <Link to="edit" params={{path: urlPath}}>{atch['_id']} ({atch.type})</Link>
        </li>
      )
    });

    if (items.length == 0) {
      items.push(
        <li key="_missing">
          <em>{i18n.trans('NO_ATTACHMENTS')}</em>
        </li>
      );
    }

    return (
      <div key="attachments" className="section">
        <h3>{i18n.trans('ATTACHMENTS')}</h3>
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

    sections.push(this.renderAlts());

    if (this.state.canHaveChildren) {
      sections.push(this.renderChildActions());
    }

    if (this.state.canHaveAttachments) {
      sections.push(this.renderAttachmentActions());
    }

    return <div className="sidebar-wrapper">{sections}</div>;
  }
}

module.exports = Sidebar;
