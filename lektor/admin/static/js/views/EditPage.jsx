'use strict';

var React = require('react');
var Router = require('react-router');

var RecordState = require('../mixins/RecordState');
var NavigationConfirmationMixin = require('../mixins/NavigationConfirmationMixin');
var utils = require('../utils');
var widgets = require('../widgets');
var {gettext} = utils;


function isIllegalField(name) {
  switch (name) {
    case '_id':
    case '_expose':
    case '_hidden':
    case '_path':
    case '_gid':
    case '_model':
    case '_attachment_for':
    case '_attachment_type':
      return true;
  }
  return false;
}



var EditPage = React.createClass({
  mixins: [
    RecordState,
    Router.Navigation,
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

  componentWillUnmount: function() {
    console.log('UNMOUNT');
  },

  componentWillReceiveProps: function(nextProps) {
    this.syncEditor();
  },

  hasPendingChanges: function() {
    return this.state.hasPendingChanges;
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
      if (isIllegalField(field.name)) {
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
    }
    return null;
  },

  renderFormFields: function() {
    var fields = this.state.recordDataModel.fields.map(function(field) {
      if (isIllegalField(field.name)) {
        return null;
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

      var placeholder = this.getPlaceholderForField(field);

      return (
        <dl key={field.name} className={className}>
          <dt>{field.label}</dt>
          <dd><Widget
            value={value}
            onChange={this.onValueChange.bind(this, field)}
            type={field.type}
            placeholder={placeholder}
          /></dd>
        </dl>
      );
    }.bind(this));

    return <div>{fields}</div>;
  },

  render: function() {
    // we have not loaded anything yet.
    if (this.state.recordInfo === null) {
      return null;
    }

    return (
      <div className="edit-area">
        <h2>{gettext('Edit “%s”').replace('%s', this.getLabel())}</h2>
        {this.renderFormFields()}
        <div className="actions">
          <button type="submit" className="btn btn-primary"
            onClick={this.saveChanges}>{gettext('Save')}</button>
        </div>
      </div>
    );
  }
});

module.exports = EditPage;
