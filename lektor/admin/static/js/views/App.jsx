'use strict';

var React = require('react');
var Router = require("react-router");
var {Link, RouteHandler} = Router;

var BreadCrumbs = require('../components/BreadCrumbs');

var App = React.createClass({
  render: function() {
    return (
      <div>
        <header>
          <h1>Lektor Admin</h1>
          <BreadCrumbs/>
        </header>
        <RouteHandler/>
      </div>
    );
  }
});

module.exports = App;
