'use strict';

var React = require('react');

var primitiveWidgets = require('./widgets/primitiveWidgets');
var multiWidgets = require('./widgets/multiWidgets');
var flowWidget = require('./widgets/flowWidget');
var fakeWidgets = require('./widgets/fakeWidgets');
var {BasicWidgetMixin} = require('./widgets/mixins');


var widgetComponents = {
  'string': primitiveWidgets.SingleLineTextInputWidget,
  'strings': primitiveWidgets.MultiLineTextInputWidget,
  'date': primitiveWidgets.DateInputWidget,
  'integer': primitiveWidgets.IntegerInputWidget,
  'boolean': primitiveWidgets.BooleanInputWidget,
  'url': primitiveWidgets.UrlInputWidget,
  'slug': primitiveWidgets.SlugInputWidget,
  'text': primitiveWidgets.MultiLineTextInputWidget,
  'html': primitiveWidgets.MultiLineTextInputWidget,
  'markdown': primitiveWidgets.MultiLineTextInputWidget,
  'flow': flowWidget.FlowWidget,
  'sortkey': primitiveWidgets.IntegerInputWidget,
  'checkboxes': multiWidgets.CheckboxesInputWidget,
  'select': multiWidgets.SelectInputWidget,
  'line': fakeWidgets.LineWidget,
  'spacing': fakeWidgets.SpacingWidget,
  'info': fakeWidgets.InfoWidget,
  'heading': fakeWidgets.HeadingWidget,
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

function getWidgetComponentWithFallback(type) {
  return widgetComponents[type.name] || FallbackWidget;
}


module.exports = {
  getWidgetComponent: getWidgetComponent,
  getWidgetComponentWithFallback: getWidgetComponentWithFallback,
  FallbackWidget: FallbackWidget
};
