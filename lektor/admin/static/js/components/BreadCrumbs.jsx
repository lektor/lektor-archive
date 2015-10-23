'use strict';

var React = require('react');
var Router = require("react-router");
var {Link, RouteHandler} = Router;

var RecordComponent = require('./RecordComponent');
var utils = require('../utils');
var i18n = require('../i18n');
var dialogSystem = require('../dialogSystem');
var FindFiles = require('../dialogs/findFiles');
var Publish = require('../dialogs/publish');


class BreadCrumbs extends RecordComponent {

  constructor(props) {
    super(props);
    this.state = {
      recordPathInfo: null,
    };
    this._onKeyPress = this._onKeyPress.bind(this);
  }

  componentDidMount() {
    super();
    this.updateCrumbs();
    window.addEventListener('keydown', this._onKeyPress);
  }

  componentWillReceiveProps(nextProps) {
    super(nextProps);
    this.updateCrumbs();
  }

  componentWillUnmount() {
    window.removeEventListener('keydown', this._onKeyPress);
  }

  updateCrumbs() {
    var path = this.getRecordPath();
    if (path === null) {
      this.setState({
        recordPathInfo: null
      });
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

  _onKeyPress(event) {
    // meta+g is open find files
    if (event.which == 71 && utils.isMetaKey(event)) {
      event.preventDefault();
      dialogSystem.showDialog(FindFiles);
    }
  }

  _onCloseClick(e) {
    e.preventDefault();
    utils.loadData('/previewinfo', {
      path: this.getRecordPath(),
      alt: this.getRecordAlt()
    })
    .then((resp) => {
      if (resp.url === null) {
        window.location.href = utils.getCanonicalUrl('/');
      } else {
        window.location.href = utils.getCanonicalUrl(resp.url);
      }
    });
  }

  _onFindFiles(e) {
    e.preventDefault();
    dialogSystem.showDialog(FindFiles);
  }

  _onPublish(e) {
    e.preventDefault();
    dialogSystem.showDialog(Publish);
  }

  render() {
    var crumbs = [];
    var target = this.isRecordPreviewActive() ? 'preview' : 'edit';
    var lastItem = null;

    if (this.state.recordPathInfo != null) {
      crumbs = this.state.recordPathInfo.segments.map((item) => {
        var urlPath = this.getUrlRecordPathWithAlt(item.path);
        var label = item.label_i18n ? i18n.trans(item.label_i18n) : item.label;
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
    } else {
      crumbs = (
        <li><Link to={'edit'} params={{path: 'root'}}>{i18n.trans('BACK_TO_OVERVIEW')}</Link></li>
      )
    }

    return (
      <div className="breadcrumbs">
        <ul className="breadcrumb container">
          {this.props.children}
          {crumbs}
          {lastItem && lastItem.can_have_children ? (
            <li className="new-record-crumb">
              <Link to="add-child" params={{path: this.getUrlRecordPathWithAlt(
                lastItem.path)}}>+</Link>
            </li>
          ) : null}
          {' ' /* this space is needed for chrome ... */}
          <li className="meta">
            <a href="#" onClick={
              this._onFindFiles.bind(this)}>{i18n.trans('FIND_FILES')}</a>
            <a href="#" onClick={
              this._onPublish.bind(this)}>{i18n.trans('PUBLISH')}</a>
            <a href="/" onClick={
              this._onCloseClick.bind(this)}>{i18n.trans('RETURN_TO_WEBSITE')}</a>
          </li>
        </ul>
      </div>
    );
  }
}

module.exports = BreadCrumbs;
