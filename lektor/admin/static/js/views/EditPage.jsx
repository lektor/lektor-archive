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
      case '_alt':
      case '_model':
      case '_attachment_for':
        return true;
      case '_attachment_type':
        return !this.state.recordInfo.is_attachment;
    }
    return false;
  }

  syncEditor() {
    utils.loadData('/rawrecord', {
      path: this.getRecordPath(),
      alt: this.getRecordAlt()
    })
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
    var alt = this.getRecordAlt();
    var newData = this.getValues();
    utils.apiRequest('/rawrecord', {json: {
        data: newData, path: path, alt: alt}, method: 'PUT'})
      .then((resp) => {
        this.setState({
          hasPendingChanges: false
        }, function() {
          this.context.router.transitionTo('preview', {
            path: this.getUrlRecordPathWithAlt(path)
          });
        });
      });
  }

  browseFs(event) {
    utils.apiRequest('/browsefs', {data: {
      path: this.getRecordPath(),
      alt: this.getRecordAlt()
    }, method: 'POST'})
      .then((resp) => {
        if (!resp.okay) {
          alert(i18n.trans('ERROR_CANNOT_BROWSE_FS'));
        }
      });
  }

  deleteRecord(event) {
    this.context.router.transitionTo('delete', {
      path: this.getUrlRecordPathWithAlt()
    });
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
          <dt>{i18n.trans(field.label_i18n)}</dt>
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
    if (this.state.recordInfo.can_be_deleted) {
      deleteButton = (
        <button type="submit" className="btn btn-default"
          onClick={this.deleteRecord.bind(this)}>{i18n.trans('DELETE')}</button>
      );
    }

    var title = this.state.recordInfo.is_attachment
      ? i18n.trans('EDIT_ATTACHMENT_METADATA_OF')
      : i18n.trans('EDIT_PAGE_NAME');

    var label = this.state.recordInfo.label_i18n
      ? i18n.trans(this.state.recordInfo.label_i18n)
      : this.state.recordInfo.label;

    return (
      <div className="edit-area">
        <h2>{title.replace('%s', label)}</h2>
        {this.renderFormFields()}
        <div className="actions">
          <button type="submit" className="btn btn-primary"
            onClick={this.saveChanges.bind(this)}>{i18n.trans('SAVE_CHANGES')}</button>
          {deleteButton}
          <button type="submit" className="btn btn-default"
            onClick={this.browseFs.bind(this)}>{i18n.trans('BROWSE_FS')}</button>
        </div>
      </div>
    );
  }
}

module.exports = EditPage;
