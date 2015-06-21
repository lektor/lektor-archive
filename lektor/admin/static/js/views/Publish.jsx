'use strict';

var React = require('react');
var Component = require('../components/Component');

var utils = require('../utils');
var i18n = require('../i18n');


class Publish extends Component {

  constructor(props) {
    super(props);

    this.state = {
      servers: [],
      activeTarget: null,
      log: [],
      currentState: 'IDLE'
    };
  }

  componentDidMount() {
    super();
    this.syncDialog();
  }

  componentWillReceiveProps(nextProps) {
    this.syncDialog();
  }

  syncDialog() {
    utils.loadData('/servers')
      .then((resp) => {
        this.setState({
          servers: resp.servers,
          activeTarget: resp.servers[0].target
        })
      });
  }

  isSaveToPublish() {
    return this.state.currentState === 'IDLE' ||
      this.state.currentState === 'DONE';
  }

  doPublish() {
    if (this.isSaveToPublish()) {
      this._beginBuild();
    }
  }

  _beginBuild() {
    this.setState({
      log: [],
      currentState: 'BUILDING'
    });
    utils.apiRequest('/build', {
      method: 'POST'
    }).then((resp) => {
      this._beginPublish();
    });
  }

  _beginPublish() {
    this.setState({
      currentState: 'PUBLISH'
    });

    var es = new EventSource(utils.getApiUrl('/publish') +
      '?target=' + encodeURIComponent(this.state.activeTarget));
    es.addEventListener('message', (event) => {
      var data = JSON.parse(event.data);
      if (data === null) {
        this.setState({
          currentState: 'DONE'
        });
        es.close();
      } else {
        this.setState({
          log: this.state.log.concat(data.msg)
        });
      }
    });
  }

  onSelectServer(event) {
    this.setState({
      activeTarget: event.target.value
    })
  }

  componentDidUpdate() {
    super();
    var node = React.findDOMNode(this.refs.log);
    if (node !== null) {
      node.scrollTop = node.scrollHeight;
    }
  }

  render() {
    var servers = this.state.servers.map((server) => {
      return (
        <option value={server.target} key={server.id}>
          {server.name + ' (' + server.short_target + ')'}
        </option>
      );
    });

    var progress = null;
    if (this.state.currentState !== 'IDLE') {
      progress = (
        <div>
          <h3>{this.state.currentState !== 'DONE'
            ? i18n.trans('CURRENTLY_PUBLISHING')
            : i18n.trans('PUBLISH_DONE')}</h3>
          <pre>{i18n.trans('STATE') + ': ' +
            i18n.trans('PUBLISH_STATE_' + this.state.currentState)}</pre>
          <pre ref="log" className="build-log">{this.state.log.join('\n')}</pre>
        </div>
      );
    }

    return (
      <div>
        <h2>{i18n.trans('PUBLISH')}</h2>
        <p>{i18n.trans('PUBLISH_NOTE')}</p>
        <dl>
          <dt>{i18n.trans('PUBLISH_SERVER')}</dt>
          <dd><div className="input-group">
            <select value={this.state.activeTarget}
              onChange={this.onSelectServer.bind(this)}
              className="form-control">{servers}</select>
          </div></dd>
        </dl>
        <div className="actions">
          <button type="submit" className="btn btn-primary"
            disabled={!this.isSaveToPublish()}
            onClick={this.doPublish.bind(this)}>{i18n.trans('PUBLISH')}</button>
        </div>
        {progress}
      </div>
    );
  }
}

module.exports = Publish;