'use strict';

var React = require('react');
var {InputWidgetMixin, BasicWidgetMixin, ValidationFailure} = require('./mixins');
var utils = require('../utils');

var SingleLineTextInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  getInputType: function() {
    return 'text';
  },

  getInputAddon: function() {
    return <span className="input-group-addon">txt</span>;
  }
});

var SlugInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  postprocessValue: function(value) {
    return value.replace(/\s+/g, '-');
  },

  getInputType: function() {
    return 'text';
  },

  getInputAddon: function() {
    return <span className="input-group-addon">slug</span>;
  }
});

var IntegerInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  getValidationFailureImpl: function() {
    if (this.state.value && !this.state.value.match(/^\d+$/)) {
      return new ValidationFailure({
        message: 'Not a valid number'
      });
    }
    return null;
  },

  getInputType: function() {
    return 'text';
  },

  getInputAddon: function() {
    return <span className="input-group-addon">0</span>;
  }
});

var UrlInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  getValidationFailureImpl: function() {
    if (this.state.value && !utils.isValidUrl(this.state.value)) {
      return new ValidationFailure({
        message: 'Not a valid URL'
      });
    }
    return null;
  },

  getInputType: function() {
    return 'text';
  },

  getInputAddon: function() {
    return <span className="input-group-addon">url</span>;
  }
});

var MultiLineTextInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  onChange: function(event) {
    this.setState({
      value: event.target.value
    }, function() {
      this.notifyChange();
    }.bind(this));
  },

  render: function() {
    var {defaultValue, ...otherProps} = this.props;
    var className = (className || '');

    return (
      <div className={className}>
        <textarea
          rows="10"
          className="form-control"
          {...otherProps}
          value={this.state.value}
          onChange={this.onChange} />
      </div>
    )
  }
});

var BooleanInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  onChange: function(event) {
    if (event.target.checked != this.isChecked()) {
      this.setState({
        value: event.target.checked ? 'yes' : 'no'
      }, function() {
        this.notifyChange();
      }.bind(this));
    }
  },

  isChecked: function() {
    var val = this.state.value.toLowerCase();
    if (val == 'true' || val == 'yes' || val == '1') {
      return true;
    }
    return false;
  },

  render: function() {
    var {className, ...otherProps} = this.props;
    className = (className || '') + ' checkbox';

    return (
      <div className={className}>
        <label>
          <input type="checkbox"
            {...otherProps}
            checked={this.isChecked()}
            onChange={this.onChange} />
        </label>
      </div>
    )
  }
});

module.exports = {
  SingleLineTextInputWidget: SingleLineTextInputWidget,
  SlugInputWidget: SlugInputWidget,
  IntegerInputWidget: IntegerInputWidget,
  UrlInputWidget: UrlInputWidget,
  MultiLineTextInputWidget: MultiLineTextInputWidget,
  BooleanInputWidget: BooleanInputWidget
};
