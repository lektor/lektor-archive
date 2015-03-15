'use strict';

var React = require('react');
var {BasicWidgetMixin, ValidationFailure} = require('./mixins');
var utils = require('../utils');

function isTrue(value) {
  return value == 'true' || value == 'yes' || value == '1';
}


var InputWidgetMixin = {
  mixins: [BasicWidgetMixin],

  onChange: function(event) {
    var value = event.target.value;
    if (this.postprocessValue) {
      value = this.postprocessValue(value);
    }
    this.props.onChange(value);
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

  postprocessValue: function(value) {
    return value.match(/^\s*(.*?)\s*$/)[1];
  },

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
  mixins: [BasicWidgetMixin],

  onChange: function(event) {
    this.recalculateSize();
    if (this.props.onChange) {
      this.props.onChange(event.target.value);
    }
  },

  componentDidMount: function() {
    this.recalculateSize();
    window.addEventListener('resize', this.recalculateSize);
  },

  componentWillUnmount: function() {
    window.removeEventListener('resize', this.recalculateSize);
  },

  componentDidUpdate: function(prevProps) {
    this.recalculateSize();
  },

  isInAutoResizeMode: function() {
    return this.props.rows === undefined;
  },

  recalculateSize: function() {
    if (!this.isInAutoResizeMode()) {
      return;
    }
    var diff;
    var node = this.refs.ta.getDOMNode();

    if (window.getComputedStyle) {
      var s = window.getComputedStyle(node);
      if (s.getPropertyValue('box-sizing') === 'border-box' ||
          s.getPropertyValue('-moz-box-sizing') === 'border-box' ||
          s.getPropertyValue('-webkit-box-sizing') === 'border-box') {
        diff = 0;
      } else {
        diff = (
          parseInt(s.getPropertyValue('padding-bottom') || 0, 10) +
          parseInt(s.getPropertyValue('padding-top') || 0, 10)
        );
      }
    } else {
      diff = 0;
    }

    var updateScrollPosition = jQuery(node).is(':focus');
    var wasAtBottom = utils.scrolledToBottom();
    var oldScrollTop = document.body.scrollTop;
    var oldHeight = jQuery(node).outerHeight();

    node.style.height = 'auto';
    var newHeight = (node.scrollHeight - diff);
    node.style.height = newHeight + 'px';

    if (updateScrollPosition) {
      window.scrollTo(
        document.body.scrollLeft, oldScrollTop + (newHeight - oldHeight));
    }
  },

  render: function() {
    var {className, type, onChange, style, ...otherProps} = this.props;
    var className = (className || '');

    style = style || {};
    if (this.isInAutoResizeMode()) {
      style.display = 'block';
      style.overflow = 'hidden';
      style.resize = 'none';
    }

    return (
      <div className={className}>
        <textarea
          ref="ta"
          className="form-control"
          onChange={onChange ? this.onChange : undefined}
          style={style}
          {...otherProps} />
      </div>
    )
  }
});

var BooleanInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  onChange: function(event) {
    this.props.onChange(event.target.checked ? 'yes' : 'no');
  },

  render: function() {
    var {className, type, onChange, value, ...otherProps} = this.props;
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
