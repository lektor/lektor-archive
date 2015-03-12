'use strict';

var React = require('react');
var utils = require('../utils');


function choiceSetFromValue(value) {
  return value.split(',').map(function(x) {
    return x.match(/^\s*(.*?)\s*$/)[1];
  });
}

var CheckboxesInputWidget = React.createClass({
  propTypes: {
    value: React.PropTypes.string,
    type: React.PropTypes.object,
    onChange: React.PropTypes.func
  },

  getInitialState: function() {
    return {
      activeChoices: choiceSetFromValue(this.props.value)
    };
  },

  componentWillReceiveProps: function(nextProps) {
    if (this.props.value != nextProps.value) {
      this.setState({
        activeChoices: choiceSetFromValue(nextProps.value)
      })
    }
  },

  onChange: function(field, event) {
    var activeChoices = utils.flipSetValue(this.state.activeChoices,
                                           field, event.target.checked);
    this.setState({
      activeChoices: activeChoices
    }, function() {
      if (this.props.onChange) {
        this.props.onChange(activeChoices.join(', '))
      }
    }.bind(this));
  },

  isActive: function(field) {
    for (var i = 0; i < this.state.activeChoices.length; i++) {
      if (this.state.activeChoices[i] === field) {
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
