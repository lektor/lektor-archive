'use strict';

var React = require('react');
var {InputWidgetMixin, BasicWidgetMixin, ValidationFailure} = require('./mixins');
var utils = require('../utils');

function isTrue(value) {
  return value == 'true' || value == 'yes' || value == '1';
}


var InputWidgetMixin = {
  propTypes: {
    value: React.PropTypes.string,
    type: React.PropTypes.object,
    onChange: React.PropTypes.func
  },

  getValidationFailure: function() {
    if (this.getValidationFailureImpl) {
      return this.getValidationFailureImpl();
    }
    return null;
  },

  onChange: function(event) {
    this.props.onChange(event.target.value);
  },

  render: function() {
    var {type, onChange, className, ...otherProps} = this.props;
    var help = null;
    var failure = this.getValidationFailure();
    var className = (className || '');
    className += ' input-group';

    if (failure !== null) {
      className += ' has-feedback has-' + failure.type;
      var valClassName = 'validation-block validation-block-' + failure.type;
      help = <div className={valClassName}>{failure.message}</div>;
    }

    var addon = this.getInputAddon ? this.getInputAddon() : null;

    return (
      <div className="form-group">
        <div className={className}>
          <input
            type={this.getInputType()}
            className="form-control"
            onChange={onChange ? this.onChange : undefined}
            {...otherProps} />
          {addon}
        </div>
        {help}
      </div>
    )
  }
};


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
    if (this.props.value && !this.props.value.match(/^\d+$/)) {
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
    if (this.props.value && !utils.isValidUrl(this.props.value)) {
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

  onChange: function(event) {
    if (this.props.onChange) {
      this.props.onChange(event.target.value)
    }
  },

  render: function() {
    var {type, onChange, ...otherProps} = this.props;
    var className = (className || '');

    return (
      <div className={className}>
        <textarea
          rows="10"
          className="form-control"
          onChange={onChange ? this.onChange : undefined}
          {...otherProps} />
      </div>
    )
  }
});

var BooleanInputWidget = React.createClass({

  onChange: function(event) {
    this.props.onChange(event.target.checked ? 'yes' : 'no');
  },

  render: function() {
    var {className, onChange, value, ...otherProps} = this.props;
    className = (className || '') + ' checkbox';

    return (
      <div className={className}>
        <label>
          <input type="checkbox"
            {...otherProps}
            checked={isTrue(value)}
            onChange={onChange ? this.onChange : undefined} />
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
