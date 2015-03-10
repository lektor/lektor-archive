'use strict';

var React = require('react');

var primitiveWidgets = require('./widgets/primitiveWidgets');
var multiWidgets = require('./widgets/multiWidgets');


// primitive widgets do not really need a fancy factory
var basicWidgets = {
  'string': primitiveWidgets.SingleLineTextInputWidget,
  'integer': primitiveWidgets.IntegerInputWidget,
  'boolean': primitiveWidgets.BooleanInputWidget,
  'url': primitiveWidgets.UrlInputWidget,
  'slug': primitiveWidgets.SlugInputWidget,
  'text': primitiveWidgets.MultiLineTextInputWidget,
  'html': primitiveWidgets.MultiLineTextInputWidget,
  'markdown': primitiveWidgets.MultiLineTextInputWidget
};

// widgets that come with custom factories
var complexWidgets = {
  'checkboxes': multiWidgets.createCheckboxInputWidget
}


var FallbackWidget = React.createClass({
  propTypes: {
    name: React.PropTypes.string
  },

  render: function() {
    return (
      <div>
        <em>Widget for "{this.props.name}" not implemented</em>
      </div>
    )
  }
});


function createWidget(type, value, props) {
  props = props || {};
  value = value || '';

  var Widget = basicWidgets[type.name];
  if (Widget !== undefined) {
    return <Widget defaultValue={value} {...props} />
  }

  var factory = complexWidgets[type.name];
  if (factory !== undefined) {
    return factory(type, value, props);
  }

  return <FallbackWidget name={type.name} />
}


module.exports = {
  createWidget: createWidget
};
