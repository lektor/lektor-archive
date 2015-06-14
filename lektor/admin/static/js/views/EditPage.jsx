'use strict';

var React = require('react');
var Router = require('react-router');

var ToggleGroup = require('../components/ToggleGroup');
var RecordEditComponent = require('../components/RecordEditComponent');
var utils = require('../utils');
var i18n = require('../i18n');
var widgets = require('../widgets');
var {gettext} = utils;


class EditPage extends RecordEditComponent {

  constructor(props) {
    super(props);

    this.state = {
      recordInitialData: null,
      recordData: null,
      recordDataModel: null,
      recordInfo: null,
      hasPendingChanges: false
    };
  }

  componentDidMount() {
    super();
    this.syncEditor();
  }

  componentWillReceiveProps(nextProps) {
    this.syncEditor();
  }

  hasPendingChanges() {
    return this.state.hasPendingChanges;
  }

  isIllegalField(field) {
    switch (field.name) {
      case '_id':
      case '_path':
      case '_gid':
      case '_model':
      case '_attachment_for':
        return true;
      case '_attachment_type':
        return !this.state.recordInfo.is_attachment;
    }
    return false;
  }

  syncEditor() {
    utils.loadData('/rawrecord', {path: this.getRecordPath()})
    .then((resp) => {
        this.setState({
          recordInitialData: resp.data,
          recordData: {},
          recordDataModel: resp.datamodel,
          recordInfo: resp.record_info,
          hasPendingChanges: false
        });
      });
  }

  onValueChange(field, value) {
    var updates = {};
    updates[field.name] = {$set: value || ''};
    var rd = React.addons.update(this.state.recordData, updates);
    this.setState({
      recordData: rd,
      hasPendingChanges: true
    });
  }

  getValues() {
    var rv = {};
    this.state.recordDataModel.fields.forEach((field) => {
      if (this.isIllegalField(field)) {
        return;
      }

      var value = this.state.recordData[field.name];

      if (value !== undefined) {
        var Widget = widgets.getWidgetComponentWithFallback(field.type);
        if (Widget.serializeValue) {
          value = Widget.serializeValue(value, field.type);
        }
      } else {
        value = this.state.recordInitialData[field.name];
        if (value === undefined) {
          value = null;
        }
      }

      rv[field.name] = value;
    });

    return rv;
  }

  saveChanges(event) {
    var path = this.getRecordPath();
    var newData = this.getValues();
    utils.apiRequest('/rawrecord', {json: {
        data: newData, path: path}, method: 'PUT'})
      .then((resp) => {
        this.setState({
          hasPendingChanges: false
        }, function() {
          this.context.router.transitionTo('preview', {path: utils.fsToUrlPath(path)});
        });
      });
  }

  deleteRecord(event) {
    var urlPath = utils.fsToUrlPath(this.getRecordPath());
    this.context.router.transitionTo('delete', {path: urlPath});
  }

  getPlaceholderForField(field) {
    if (field.name == '_slug') {
      return this.state.recordInfo.slug_format;
    } else if (field.name == '_template') {
      return this.state.recordInfo.default_template;
    } else if (field.name == '_attachment_type') {
      return this.state.recordInfo.implied_attachment_type;
    }
    return null;
  }

  renderFormFields() {
    var fields = [];
    var systemFields = [];
    
    this.state.recordDataModel.fields.forEach((field) => {
      if (this.isIllegalField(field)) {
        return;
      }

      var className = 'field';
      if (field.name.substr(0, 1) == '_') {
        className += ' system-field';
      }

      var Widget = widgets.getWidgetComponentWithFallback(field.type);
      var value = this.state.recordData[field.name];
      if (value === undefined) {
        var value = this.state.recordInitialData[field.name] || '';
        if (Widget.deserializeValue) {
          value = Widget.deserializeValue(value, field.type);
        }
      }

      var rv = (
        <dl key={field.name} className={className}>
          <dt>{field.label}</dt>
          <dd><Widget
            value={value}
            onChange={this.onValueChange.bind(this, field)}
            type={field.type}
            placeholder={this.getPlaceholderForField(field)}
          /></dd>
        </dl>
      );

      if (field.name.substr(0, 1) == '_') {
        systemFields.push(rv);
      } else {
        fields.push(rv);
      }

    });

    return (
      <div>
        {fields}
        <ToggleGroup
          groupTitle={i18n.trans('SYSTEM_FIELDS')}
          defaultVisibility={false}>{systemFields}</ToggleGroup>
      </div>
    );
  }

  render() {
    // we have not loaded anything yet.
    if (this.state.recordInfo === null) {
      return null;
    }

    var deleteButton = null;
    if (!this.isRootRecord()) {
      deleteButton = (
        <button type="submit" className="btn btn-default"
          onClick={this.deleteRecord.bind(this)}>{i18n.trans('DELETE')}</button>
      );
    }

    var title = this.state.recordInfo.is_attachment
      ? i18n.trans('EDIT_ATTACHMENT_METADATA_OF')
      : i18n.trans('EDIT_PAGE_NAME');

    return (
      <div className="edit-area">
        <h2>{title.replace('%s', this.state.recordInfo.label)}</h2>
        {this.renderFormFields()}
        <div className="actions">
          <button type="submit" className="btn btn-primary"
            onClick={this.saveChanges.bind(this)}>{i18n.trans('SAVE_CHANGES')}</button>
          {deleteButton}
        </div>
      </div>
    );
  }
}

module.exports = EditPage;
