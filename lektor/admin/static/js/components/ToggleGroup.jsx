'use strict';

var React = require('react');


var ToggleGroup = React.createClass({
  propTypes: {
    groupTitle: React.PropTypes.string,
    defaultVisibility: React.PropTypes.bool
  },

  getInitialState: function() {
    return {
      isVisible: this.props.defaultVisibility
    }
  },

  toggle: function(event) {
    event.preventDefault();
    this.setState({
      isVisible: !this.state.isVisible
    })
  },

  render: function() {
    var {className, groupTitle, children, ...otherProps} = this.props;
    className = (className || '') + ' toggle-group';
    if (this.state.isVisible) {
      className += ' toggle-group-open';
    } else {
      className += ' toggle-group-closed';
    }

    return (
      <div className={className} {...otherProps}>
        <div className="header">
          <h4 className="toggle" onClick={this.toggle}>{groupTitle}</h4>
        </div>
        <div className="children">
          {children}
        </div>
      </div>
    )
  }
});

module.exports = ToggleGroup;
