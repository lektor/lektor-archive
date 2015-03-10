'use strict';

var React = require('react');
var {BasicWidgetMixin} = require('./mixins');
var utils = require('../utils');

var CheckboxesInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],
  propTypes: {
    choices: React.PropTypes.array
  },

  getInitialState: function() {
    return {
      activeChoices: this.props.defaultValue.split(',').map(function(x) {
        return x.match(/^\s*(.*?)\s*$/)[1];
      })
    };
  },

  onChange: function(field, event) {
    var activeChoices = utils.flipSetValue(this.state.activeChoices,
                                           field, event.target.checked);
    this.setState({
      activeChoices: activeChoices,
      value: activeChoices.join(', ')
    }, function() {
      this.notifyChange();
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
    var {className, ...otherProps} = this.props;
    className = (className || '') + ' checkbox';

    var choices = this.props.choices.map(function(item) {
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

function createCheckboxInputWidget(type, value, props) {
  return <CheckboxesInputWidget
    defaultValue={value}
    choices={type.choices}
    {...props} />;
}

module.exports = {
  createCheckboxInputWidget: createCheckboxInputWidget
};
