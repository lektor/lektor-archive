'use strict';

var React = require('react');
var utils = require('../utils');
var metaformat = require('../metaformat');
var {BasicWidgetMixin} = require('./mixins');


/* circular references require us to do this */
function getWidgetComponent(type) {
  var widgets = require('../widgets');
  return widgets.getWidgetComponent(type);
}


function parseFlowFormat(value) {
  var blocks = [];
  var buf = [];
  var lines = value.split(/\r?\n/);
  var block = null;

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];

    // leading whitespace is ignored.
    if (block === null && line.match(/^\s*$/)) {
      continue;
    }

    var blockStart = line.match(/^####\s*(.*?)\s*####\s*$/);
    if (!blockStart) {
      if (block === null) {
        // bad format :(
        return null;
      }
    } else {
      if (block !== null) {
        blocks.push([block, buf]);
        buf = [];
      }
      block = blockStart[1];
      continue;
    }

    buf.push(line);
  }

  if (block !== null) {
    blocks.push([block, buf]);
  }

  return blocks;
}

function serializeFlowFormat(blocks) {
  return blocks.map(function(block) {
    var [blockName, lines] = block;
    return '#### ' + blockName + ' ####\n' + lines.join('');
  }).join('\n');
}

function deserializeFlowBlock(flowBlockModel, lines, localId) {
  var data = {};

  metaformat.tokenize(lines).forEach(function(item) {
    var [key, lines] = item;
    var field = flowBlockModel.fields[key];
    var value = lines.join('');
    var Widget = null;

    if (field !== undefined) {
      Widget = getWidgetComponent(field.type);
      if (Widget && Widget.deserializeValue) {
        value = Widget.deserializeValue(value, field.type);
      }
    }

    data[key] = value;
  });

  return {
    localId: localId || null,
    flowBlockModel: flowBlockModel,
    data: data
  }
}

function serializeFlowBlock(flockBlockModel, data) {
  var rv = [];
  flockBlockModel.fields.forEach(function(field) {
    var Widget = getWidgetComponent(field.type);
    if (Widget === null) {
      return;
    }

    var value = data[field.name];
    if (value === undefined || value === null) {
      return;
    }

    if (Widget.deserializeValue) {
      value = Widget.deserializeValue(value, field.type);
    }

    rv.push([field.name, value]);
  });
  return metaformat.serialize(rv);
}

// ever growing counter of block ids.  Good enough for what we do I think.
var lastBlockId = 0;


var FlowWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  statics: {
    deserializeValue: function(value, type) {
      return parseFlowFormat(value).map(function(item) {
        var [id, lines] = item;
        var flowBlock = type.flowblocks[id];
        if (flowBlock !== undefined) {
          return deserializeFlowBlock(flowBlock, lines, ++lastBlockId);
        }
        return null;
      }.bind(this));
    },

    serializeValue: function(value) {
      return serializeFlowFormat(value.map(function(item) {
        return [
          item.flowBlockModel.id,
          serializeFlowBlock(item.flowBlockModel, item.data)
        ];
      }));
    }
  },

  renderBlock: function(flowBlockModel, data) {
    var fields = flowBlockModel.fields.map(function(field) {
      if (field.name == '_flowblock') {
        return null;
      }

      var value = data[field.name];
      var Widget = getWidgetComponent(field.type);
      if (!Widget) {
        return null;
      }

      function onValueChange(value) {
        data[field.name] = value;
        this.props.onChange(this.props.value);
      }

      return (
        <dl key={field.name}>
          <dt>{field.label}</dt>
          <dd><Widget
            value={value}
            onChange={this.props.onChange ? onValueChange.bind(this) : undefined}
            type={field.type}
          /></dd>
        </dl>
      );
    }.bind(this));

    return (
      <div className="flow-block">
        <h4 className="block-name">{flowBlockModel.name}</h4>
        {fields}
      </div>
    );
  },

  renderCurrentBlocks: function() {
    return this.props.value.map(function(blockInfo) {
      // bad block is no block
      if (blockInfo === null) {
        return null;
      }

      return (
        <div key={blockInfo.localId}>
          {this.renderBlock(blockInfo.flowBlockModel, blockInfo.data)}
        </div>
      );
    }.bind(this));
  },

  render: function() {
    var {className, value, type, ...otherProps} = this.props;
    className = (className || '') + ' flow';

    return (
      <div className={className}>
        {this.renderCurrentBlocks()}
      </div>
    );
  }
});

module.exports = {
  FlowWidget: FlowWidget
};
