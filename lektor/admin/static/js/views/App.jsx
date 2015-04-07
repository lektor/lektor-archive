'use strict';

var React = require('react');
var Router = require("react-router");
var {RouteHandler} = Router;

var BreadCrumbs = require('../components/BreadCrumbs');
var Sidebar = require('../components/Sidebar');
var Component = require('../components/Component');


class App extends Component {

  render() {
    return (
      <div className="application">
        <header>
          <BreadCrumbs>
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
