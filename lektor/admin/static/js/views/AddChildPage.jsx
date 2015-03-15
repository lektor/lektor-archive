'use strict';

var qs = require('querystring');
var React = require('react');
var Router = require('react-router');

var RecordState = require('../mixins/RecordState');
var utils = require('../utils');
var widgets = require('../widgets');
var {gettext, ngettext} = utils;


function getGoodDefaultModel(models) {
  if (models.page !== undefined) {
    return 'page';
  }
  var choices = Object.keys(models);
  choices.sort();
  return choices[0];
}


var AddChildPage = React.createClass({
  mixins: [
    RecordState,
    Router.Navigation
  ],

  getInitialState: function() {
    return {
      newChildInfo: null,
      id: undefined,
      selectedModel: null
    }
  },

  componentDidMount: function() {
    this.syncDialog();
  },

  componentWillReceiveProps: function(nextProps) {
    this.syncDialog();
  },

  syncDialog: function() {
    utils.loadData('/newrecord', {path: this.getRecordPath()})
      .then(function(resp) {
        var selectedModel = resp.implied_model;
        if (!selectedModel) {
          selectedModel = getGoodDefaultModel(resp.available_models);
        }

        this.setState({
          newChildInfo: resp,
          id: undefined,
          primary: undefined,
          selectedModel: selectedModel
        });
      }.bind(this));
  },

  onValueChange: function(id, value) {
    var obj = {};
    obj[id] = value;
    this.setState(obj);
  },

  getAvailableModels: function() {
    var rv = [];
    for (var key in this.state.newChildInfo.available_models) {
      var model = this.state.newChildInfo.available_models[key];
      rv.push(model);
    }
    rv.sort(function(a, b) {
      return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
    });
    return rv;
  },

  onModelSelected: function(event) {
    this.setState({
      selectedModel: event.target.value
    });
  },

  getImpliedId: function() {
    return utils.slugify(this.state.primary || '').toLowerCase();
  },

  getPrimaryField: function() {
    return this.state.newChildInfo.available_models[
      this.state.selectedModel].primary_field;
  },

  createRecord: function() {
    var id = this.state.id || this.getImpliedId();
    if (!id) {
      alert(gettext('Error: No ID provided :('));
      return;
    }

    var data = {};
    var params = {id: id, path: this.getRecordPath(), data: data};
    if (!this.state.newChildInfo.implied_model) {
      data._model = this.state.selectedModel;
    }
    var primaryField = this.getPrimaryField();
    if (primaryField) {
      data[primaryField.name] = this.state.primary;
    }

    utils.apiRequest('/newrecord', {json: params, method: 'POST'})
      .then(function(resp) {
        if (resp.exists) {
          alert(gettext('Error: Record with this ID (%s) exists already.')
               .replace('%s', id));
        } else if (!resp.valid_id) {
          alert(gettext('Error: The ID provided (%s) is not allowed.')
               .replace('%s', id));
        } else {
          var urlPath = utils.fsToUrlPath(resp.path);
          this.transitionTo('edit', {path: urlPath});
        }
      }.bind(this));
  },

  renderFields: function() {
    var fields = [];

    if (!this.state.newChildInfo.implied_model) {
      var choices = this.getAvailableModels().map(function(model) {
        return (
          <option value={model.id} key={model.id}>{model.name}</option>
        );
      });
      fields.push(
        <dl key="_model">
          <dt>{gettext('Model')}</dt>
          <dd><select value={this.state.selectedModel}
              className="form-control"
              onChange={this.onModelSelected}>
            {choices}
          </select></dd>
        </dl>
      );
    }

    var addField = function(id, field, placeholder) {
      var value = this.state[id];
      var Widget = widgets.getWidgetComponentWithFallback(field.type);
      if (Widget.deserializeValue) {
        value = Widget.deserializeValue(value, field.type);
      }
      fields.push(
        <dl key={field.name}>
          <dt>{field.label}</dt>
          <dd><Widget
            value={value}
            placeholder={placeholder}
            onChange={this.onValueChange.bind(this, id)}
            type={field.type}
          /></dd>
        </dl>
      );
    }.bind(this);

    var primaryField = this.getPrimaryField();
    if (primaryField) {
      addField('primary', primaryField);
    }

    addField('id', {
      name: '_id',
      label: 'ID',
      type: {name: 'string'}
    }, this.getImpliedId());

    return fields;
  },

  render: function() {
    var nci = this.state.newChildInfo;

    if (!nci) {
      return null;
    }

    return (
      <div>
        <h2>{gettext('Add Child to “%s”').replace(
          '%s', this.state.newChildInfo.label)}</h2>
        <p>{gettext('You can add a new child to the page here.  Note that ' +
                    'the model or ID cannot be easily changed afterwards.')}</p>
        {this.renderFields()}
        <div className="actions">
          <button className="btn btn-primary" onClick={this.createRecord}>{
            gettext('Create Page')}</button>
        </div>
      </div>
    );
  }
});

module.exports = AddChildPage;
