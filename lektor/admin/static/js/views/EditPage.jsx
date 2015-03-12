'use strict';

var React = require('react');
var Router = require('react-router');

var RecordState = require('../mixins/RecordState');
var utils = require('../utils');
var widgets = require('../widgets');
var {gettext} = utils;


function isHiddenField(name) {
  switch (name) {
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
    RecordState
  ],

  getInitialState: function() {
    return {
      recordData: null,
      recordDataModel: null,
      recordInfo: null
    }
  },

  componentDidMount: function() {
    this.syncEditor();
  },

  componentWillReceiveProps: function(nextProps) {
    this.syncEditor();
  },

  syncEditor: function() {
    utils.loadData('/rawrecord', {path: this.getRecordPath()})
      .then(function(resp) {
        this.setState({
          recordData: resp.data,
          recordDataModel: resp.datamodel,
          recordInfo: resp.record_info,
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

  onValueChange: function(field, value) {
    var updates = {};
    updates[field.name] = {$set: value || ''};
    var rd = React.addons.update(this.state.recordData, updates);
    this.setState({
      recordData: rd
    });
  },

  renderFormFields: function() {
    var fields = this.state.recordDataModel.fields.map(function(field) {
      if (isHiddenField(field.name)) {
        return null;
      }

      var value = this.state.recordData[field.name] || '';
      var Widget = widgets.getWidgetComponent(field.type);
      if (!Widget) {
        Widget = widgets.FallbackWidget;
      } 

      var className = 'field';
      if (field.name.substr(0, 1) == '_') {
        className += ' system-field';
      }

      return (
        <dl key={field.name} className={className}>
          <dt>{field.label}</dt>
          <dd><Widget
            value={value}
            onChange={this.onValueChange.bind(this, field)}
            type={field.type}
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
      <div>
        <h2>{gettext('Edit “%s”').replace('%s', this.getLabel())}</h2>
        {this.renderFormFields()}
      </div>
    );
  }
});

module.exports = EditPage;
