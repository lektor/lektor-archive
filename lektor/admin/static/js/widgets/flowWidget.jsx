'use strict';

var React = require('react');
var i18n = require('../i18n');
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
  var rv = [];
  blocks.forEach(function(block) {
    var [blockName, lines] = block;
    rv.push('#### ' + blockName + '####\n');
    rv.push.apply(rv, lines);
  });

  rv = rv.join('');

  /* we need to chop of the last newline if it exists because this would
     otherwise add a newline to the last block.  This is just a side effect
     of how we serialize the meta format internally */
  if (rv[rv.length - 1] === '\n') {
    rv = rv.substr(0, rv.length - 1);
  }

  return rv;
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

  // XXX: the modification of props is questionable

  moveBlock: function(idx, offset, event) {
    event.preventDefault();

    var newIndex = idx + offset;
    if (newIndex < 0 || newIndex >= this.props.value.length) {
      return;
    }

    var tmp = this.props.value[newIndex];
    this.props.value[newIndex] = this.props.value[idx];
    this.props.value[idx] = tmp;

    if (this.props.onChange) {
      this.props.onChange(this.props.value);
    }
  },

  removeBlock: function(idx, event) {
    event.preventDefault();

    if (confirm(i18n.trans('REMOVE_FLOWBLOCK_PROMPT'))) {
      this.props.value.splice(idx, 1);
      if (this.props.onChange) {
        this.props.onChange(this.props.value);
      }
    }
  },

  addNewBlock: function(event) {
    event.preventDefault();

    var key = this.refs.new_block_choice.getDOMNode().value;
    var flowBlockModel = this.props.type.flowblocks[key];

    // this is a rather ugly way to do this, but hey, it works.
    this.props.value.push(deserializeFlowBlock(flowBlockModel, [],
                                               ++lastBlockId));
    if (this.props.onChange) {
      this.props.onChange(this.props.value);
    }
  },

  renderBlocks: function() {
    return this.props.value.map(function(blockInfo, idx) {
      // bad block is no block
      if (blockInfo === null) {
        return null;
      }

      var fields = blockInfo.flowBlockModel.fields.map(function(field) {
        var value = blockInfo.data[field.name];
        var Widget = getWidgetComponent(field.type);
        if (!Widget) {
          return null;
        }

        function onValueChange(value) {
          blockInfo.data[field.name] = value;
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
        <div key={blockInfo.localId} className="flow-block">
          <ul className="actions">
            <li><a href="#" onClick={this.moveBlock.bind(this, idx, -1)}>{i18n.trans('UP')}</a></li>
            <li><a href="#" onClick={this.moveBlock.bind(this, idx, 1)}>{i18n.trans('DOWN')}</a></li>
            <li><a href="#" onClick={this.removeBlock.bind(this, idx)}>{i18n.trans('REMOVE')}</a></li>
          </ul>
          <h4 className="block-name">{blockInfo.flowBlockModel.name}</h4>
          {fields}
        </div>
      );
    }.bind(this));
  },

  renderAddBlockSection: function() {
    var choices = [];

    for (var key in this.props.type.flowblocks) {
      var flowBlockModel = this.props.type.flowblocks[key];
      choices.push([flowBlockModel.id, flowBlockModel.name]);
    }
    choices.sort(function(a, b) {
      return a[1].toLowerCase().localeCompare(b[1].toLowerCase());
    });
    choices = choices.map(function(item) {
      var [value, title] = item;
      return <option key={value} value={value}>{title}</option>
    });

    // XXX: column layout -> something better
    return (
      <div className="add-block">
        <div className="row row-inline-thin-padding">
          <div className="col-md-8">
            <select ref="new_block_choice" className="form-control">
              {choices}
            </select>
          </div>
          <div className="col-md-4">
            <button className="btn btn-default"
              onClick={this.addNewBlock}>{i18n.trans('ADD_FLOWBLOCK')}</button>
          </div>
        </div>
      </div>
    )
  },

  render: function() {
    var {className, value, type, ...otherProps} = this.props;
    className = (className || '') + ' flow';

    return (
      <div className={className}>
        {this.renderBlocks()}
        {this.renderAddBlockSection()}
      </div>
    );
  }
});

module.exports = {
  FlowWidget: FlowWidget
};
