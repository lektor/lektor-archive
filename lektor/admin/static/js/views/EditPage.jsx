'use strict';

var React = require('react');
var Router = require('react-router');

var ToggleGroup = require('../components/ToggleGroup');
var RecordState = require('../mixins/RecordState');
var NavigationConfirmationMixin = require('../mixins/NavigationConfirmationMixin');
var utils = require('../utils');
var widgets = require('../widgets');
var {gettext} = utils;


var EditPage = React.createClass({
  mixins: [
    RecordState,
    Router.Navigation,
    Router.State,
    NavigationConfirmationMixin
  ],

  getInitialState: function() {
    return {
      recordInitialData: null,
      recordData: null,
      recordDataModel: null,
      recordInfo: null,
      hasPendingChanges: false
    }
  },

  componentDidMount: function() {
    this.syncEditor();
  },

  componentWillReceiveProps: function(nextProps) {
    this.syncEditor();
  },

  hasPendingChanges: function() {
    return this.state.hasPendingChanges;
  },

  isIllegalField: function(field) {
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
  },

  syncEditor: function() {
    utils.loadData('/rawrecord', {path: this.getRecordPath()})
      .then(function(resp) {
        this.setState({
          recordInitialData: resp.data,
          recordData: {},
          recordDataModel: resp.datamodel,
          recordInfo: resp.record_info,
          hasPendingChanges: false
        });
      }.bind(this));
  },

  onValueChange: function(field, value) {
    var updates = {};
    updates[field.name] = {$set: value || ''};
    var rd = React.addons.update(this.state.recordData, updates);
    this.setState({
      recordData: rd,
      hasPendingChanges: true
    });
  },

  getValues: function() {
    var rv = {};
    this.state.recordDataModel.fields.forEach(function(field) {
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
    }.bind(this));

    return rv;
  },

  saveChanges: function(event) {
    var path = this.getRecordPath();
    var newData = this.getValues();
    utils.apiRequest('/rawrecord', {json: {
        data: newData, path: path}, method: 'PUT'})
      .then(function(resp) {
        this.setState({
          hasPendingChanges: false
        }, function() {
          this.transitionTo('preview', {path: utils.fsToUrlPath(path)});
        });
      }.bind(this));
  },

  deleteRecord: function(event) {
    var urlPath = utils.fsToUrlPath(this.getRecordPath());
    this.transitionTo('delete', {path: urlPath});
  },

  getLabel: function() {
    var ri = this.state.recordInfo;
    if (!ri) {
      return null;
    }
    if (ri.exists) {
      return ri.label;
    }
    return ri.id;
  },

  getPlaceholderForField: function(field) {
    if (field.name == '_slug') {
      return this.state.recordInfo.slug_format;
    } else if (field.name == '_template') {
      return this.state.recordInfo.default_template;
    } else if (field.name == '_attachment_type') {
      return this.state.recordInfo.implied_attachment_type;
    }
    return null;
  },

  renderFormFields: function() {
    var fields = [];
    var systemFields = [];
    
    this.state.recordDataModel.fields.forEach(function(field) {
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

    }.bind(this));

    return (
      <div>
        {fields}
        <ToggleGroup
          groupTitle={gettext('System fields')}
          defaultVisibility={false}>{systemFields}</ToggleGroup>
      </div>
    );
  },

  render: function() {
    // we have not loaded anything yet.
    if (this.state.recordInfo === null) {
      return null;
    }

    var deleteButton = null;
    if (!this.isRootRecord()) {
      deleteButton = (
        <button type="submit" className="btn btn-default"
          onClick={this.deleteRecord}>{gettext('Delete')}</button>
      );
    }

    return (
      <div className="edit-area">
        <h2>{gettext('Edit “%s”').replace('%s', this.getLabel())}</h2>
        {this.renderFormFields()}
        <div className="actions">
          <button type="submit" className="btn btn-primary"
            onClick={this.saveChanges}>{gettext('Save changes')}</button>
          {deleteButton}
        </div>
      </div>
    );
  }
});

module.exports = EditPage;
