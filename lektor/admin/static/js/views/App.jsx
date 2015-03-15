'use strict';

var React = require('react');
var Router = require("react-router");
var {Link, RouteHandler} = Router;

var BreadCrumbs = require('../components/BreadCrumbs');
var Sidebar = require('../components/Sidebar');

var App = React.createClass({
  render: function() {
    return (
      <div className="application">
        <header>
          <BreadCrumbs/>
        </header>
        <div className="editor">
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
});

module.exports = App;
