'use strict';

var React = require('react');
var Router = require("react-router");
var {RouteHandler} = Router;

var BreadCrumbs = require('../components/BreadCrumbs');
var Sidebar = require('../components/Sidebar');
var Component = require('../components/Component');
var DialogSlot = require('../components/dialogSlot');
var ServerStatus = require('../components/serverStatus');
var dialogSystem = require('../dialogSystem');
var {DialogChangedEvent} = require('../events');
var hub = require('../hub');


class App extends Component {

  render() {
    return (
      <div className="application">
        <ServerStatus/>
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
          <DialogSlot/>
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
