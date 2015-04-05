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
          <BreadCrumbs/>
        </header>
        <div className="editor container">
          <div className="sidebar">
            <Sidebar/>
          </div>
          <div className="view">
            <RouteHandler/>
          </div>
        </div>
      </div>
    );
  }
}

module.exports = App;
