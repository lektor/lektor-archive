'use strict';

var React = require('react');
var Router = require("react-router");
var {RouteHandler} = Router;

var BreadCrumbs = require('../components/BreadCrumbs');
var Sidebar = require('../components/Sidebar');
var FindFiles = require('../components/FindFiles');
var Component = require('../components/Component');


class App extends Component {

  constructor(props) {
    super(props);
    this.state = {
      findFilesOpen: false
    };
    this.onKeyDown = this.onKeyDown.bind(this);
  }

  onToggleFindFiles(newVal) {
    if (newVal === undefined) {
      newVal = !this.state.findFilesOpen;
    }
    this.setState({
      findFilesOpen: newVal
    });
  }

  componentDidMount() {
    super();
    window.addEventListener('keydown', this.onKeyDown);
  }

  componentWillUnmount() {
    super();
    window.removeEventListener('keydown', this.onKeyDown);
  }

  onKeyDown(event) {
    if (event.metaKey && event.which == 71) {
      event.preventDefault();
      this.onToggleFindFiles(true);
    }
  }

  render() {
    return (
      <div className="application">
        <header>
          <BreadCrumbs onToggleFindFiles={this.onToggleFindFiles.bind(this)}>
            <button type="button" className="navbar-toggle"
                data-toggle="offcanvas"
                data-target=".sidebar-block">
              <span className="sr-only">Toggle navigation</span>
              <span className="icon-list"></span>
              <span className="icon-list"></span>
              <span className="icon-list"></span>
            </button>
          </BreadCrumbs>
        </header>
        {this.state.findFilesOpen ? <FindFiles onClose={
          this.onToggleFindFiles.bind(this, false)}/> : null}
        <div className="editor container">
          <div className="sidebar-block block-offcanvas block-offcanvas-left">
            <nav className="sidebar col-md-2 col-sm-3 sidebar-offcanvas">
              <Sidebar/>
            </nav>
            <div className="view col-md-10 col-sm-9">
              <RouteHandler/>
            </div>
          </div>
        </div>
      </div>
    );
  }
}

module.exports = App;
