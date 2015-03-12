'use strict';

var React = require('react');

var primitiveWidgets = require('./widgets/primitiveWidgets');
var multiWidgets = require('./widgets/multiWidgets');
var {BasicWidgetMixin} = require('./widgets/mixins');


var widgetComponents = {
  'string': primitiveWidgets.SingleLineTextInputWidget,
  'integer': primitiveWidgets.IntegerInputWidget,
  'boolean': primitiveWidgets.BooleanInputWidget,
  'url': primitiveWidgets.UrlInputWidget,
  'slug': primitiveWidgets.SlugInputWidget,
  'text': primitiveWidgets.MultiLineTextInputWidget,
  'html': primitiveWidgets.MultiLineTextInputWidget,
  'markdown': primitiveWidgets.MultiLineTextInputWidget,
  'flow': primitiveWidgets.MultiLineTextInputWidget,
  'checkboxes': multiWidgets.CheckboxesInputWidget
}


var FallbackWidget = React.createClass({
  mixins: [BasicWidgetMixin],
  render: function() {
    return (
      <div>
        <em>Widget for "{this.props.type.name}" not implemented</em>
      </div>
    )
  }
});


function getWidgetComponent(type) {
  return widgetComponents[type.name] || null;
}


module.exports = {
  getWidgetComponent: getWidgetComponent,
  FallbackWidget: FallbackWidget
};
