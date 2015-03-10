var React = require('react');

var utils = require('../utils');
var {gettext} = utils;


function ValidationFailure(options) {
  this.message = options.message || gettext('Invalid input');
  this.type = options.type || 'error';
}


var BasicWidgetMixin = {
  propTypes: {
    defaultValue: React.PropTypes.string,
    onChange: React.PropTypes.func
  },

  getInitialState: function() {
    return {
      value: this.props.defaultValue || ''
    }
  },

  getValidationFailure: function() {
    if (this.getValidationFailureImpl) {
      return this.getValidationFailureImpl();
    }
    return null;
  },

  isValid: function() {
    return this.getValidationFailure() === null;
  },

  componentWillReceiveProps: function(newProps) {
    this.setState({
      value: newProps.defaultValue || ''
    });
  },

  notifyChange: function() {
    if (this.props.onChange) {
      this.props.onChange(
        this.state.value,
        this.isValid()
      );
    }
  }
};

var InputWidgetMixin = {
  mixins: [BasicWidgetMixin],

  onChange: function(event) {
    var value = event.target.value;
    if (this.postprocessValue) {
      value = this.postprocessValue(value);
    }
    this.setState({
      value: value
    }, function() {
      this.notifyChange();
    }.bind(this));
  },

  render: function() {
    var {defaultValue, className, ...otherProps} = this.props;
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
            {...otherProps}
            value={this.state.value}
            onChange={this.onChange} />
          {addon}
        </div>
        {help}
      </div>
    )
  }
};

module.exports = {
  ValidationFailure: ValidationFailure,
  BasicWidgetMixin: BasicWidgetMixin,
  InputWidgetMixin: InputWidgetMixin
};
