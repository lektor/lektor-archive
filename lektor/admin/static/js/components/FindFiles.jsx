'use strict';

var React = require('react');
var Router = require("react-router");
var {Link, RouteHandler} = Router;

var RecordComponent = require('./RecordComponent');
var utils = require('../utils');
var i18n = require('../i18n');


class FindFiles extends RecordComponent {

  constructor(props) {
    super(props);
    this.state = {
      query: '',
      currentSelection: -1,
      results: []
    };
  }

  onCloseClick(e) {
    e.preventDefault();
    this.props.onClose();
  }

  componentDidMount() {
    super();
    React.findDOMNode(this.refs.q).focus();
  }

  onInputChange(e) {
    var q = e.target.value;

    if (q === '') {
      this.setState({
        query: '',
        results: [],
        currentSelection: -1
      });
    } else {
      this.setState({
        query: q
      });

      utils.apiRequest('/find', {
        data: {
          q: q,
          alt: this.getRecordAlt(),
          lang: i18n.currentLanguage
        },
        method: 'POST'
      }).then((resp) => {
        this.setState({
          results: resp.results,
          currentSelection: Math.min(this.state.currentSelection,
                                     resp.results.length - 1)
        });
      });
    }
  }

  onInputKey(e) {
    var sel = this.state.currentSelection;
    var max = this.state.results.length;
    if (e.which == 40) {
      e.preventDefault();
      sel = (sel + 1) % max;
    } else if (e.which == 38) {
      e.preventDefault();
      sel = (sel - 1 + max) % max;
    } else if (e.which == 27) {
      e.preventDefault();
      this.props.onClose();
    } else if (e.which == 13) {
      this.onActiveItem(this.state.currentSelection);
    }
    this.setState({
      currentSelection: sel
    });
  }

  onActiveItem(index) {
    var item = this.state.results[index];
    if (item !== undefined) {
      var target = this.isRecordPreviewActive() ? 'preview' : 'edit';
      var urlPath = this.getUrlRecordPathWithAlt(item.path);
      this.props.onClose();
      this.context.router.transitionTo(target, {path: urlPath});
    }
  }

  selectItem(index) {
    this.setState({
      currentSelection: Math.min(index, this.state.results.length - 1)
    });
  }

  renderResults() {
    var rv = [];

    var rv = this.state.results.map((result, idx) => {
      var parents = result.parents.map((item) => {
        return (
          <span className="parent">
            {item.title}
          </span>
        );
      });

      return (
        <li
          key={idx}
          className={idx == this.state.currentSelection ? 'active': ''}
          onClick={this.onActiveItem.bind(this, idx)}
          onMouseEnter={this.selectItem.bind(this, idx)}>
          {parents}
          <strong>{result.title}</strong>
        </li>
      );
    });

    return (
      <ul className="search-results">{rv}</ul>
    );
  }

  render() {
    return (
      <div className="sliding-panel container">
        <div className="col-md-6 col-md-offset-4">
          <a href="#" className="close-btn" onClick={
            this.onCloseClick.bind(this)}>{i18n.trans('CLOSE')}</a>
          <h3>{i18n.trans('FIND_FILES')}</h3>
          <div className="form-group">
            <input type="text"
              ref="q"
              className="form-control"
              value={this.state.query}
              onChange={this.onInputChange.bind(this)}
              onKeyDown={this.onInputKey.bind(this)}
              placeholder={i18n.trans('FIND_FILES_PLACEHOLDER')}/>
          </div>
          {this.renderResults()}
        </div>
      </div>
    );
  }
}

FindFiles.propTypes = {
  onClose: React.PropTypes.func
};

module.exports = FindFiles;
