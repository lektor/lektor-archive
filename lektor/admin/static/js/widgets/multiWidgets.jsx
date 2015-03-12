'use strict';

var React = require('react');
var utils = require('../utils');
var {BasicWidgetMixin} = require('./mixins');


var CheckboxesInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  statics: {
    deserializeValue: function(value) {
      return value.split(',').map(function(x) {
        return x.match(/^\s*(.*?)\s*$/)[1];
      });
    },

    serializeValue: function(value) {
      return value.join(', ');
    }
  },

  onChange: function(field, event) {
    var newValue = utils.flipSetValue(this.props.value,
                                      field, event.target.checked);
    if (this.props.onChange) {
      this.props.onChange(newValue)
    }
  },

  isActive: function(field) {
    for (var i = 0; i < this.props.value.length; i++) {
      if (this.props.value[i] === field) {
        return true;
      }
    }
    return false;
  },

  render: function() {
    var {className, value, type, ...otherProps} = this.props;
    className = (className || '') + ' checkbox';

    var choices = this.props.type.choices.map(function(item) {
      return (
        <div className={className} key={item[0]}>
          <label>
            <input type="checkbox"
              {...otherProps}
              checked={this.isActive(item[0])}
              onChange={this.onChange.bind(this, item[0])} />
            {item[1]}
          </label>
        </div>
      );
    }.bind(this));
    return (
      <div>
        {choices}
      </div>
    )
  }
});

module.exports = {
  CheckboxesInputWidget: CheckboxesInputWidget
};
