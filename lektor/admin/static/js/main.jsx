'use strict';

var React = require('react');
var Router = require("react-router");
var {Route, DefaultRoute, NotFoundRoute} = Router;
var Promise = require('bluebird');

Promise.onPossiblyUnhandledRejection(function(error) {
  console.log('Unhandled promise error:', error);
});

var BadRoute = React.createClass({
  render: function() {
    return (
      <div>
        <h2>Nothing to see here</h2>
        <p>There is really nothing to see here.</p>
      </div>
    );
  }
});

var routes = (function() {
  // route targets
  var App = require('./views/App');
  var Dash = require('./views/Dash');
  var EditPage = require('./views/EditPage');

  // route setup
  return (
    <Route name="dash" path={$LEKTOR_CONFIG.admin_root} handler={App}>
      <Route name="edit" path=":path/edit" handler={EditPage}/>
      <DefaultRoute handler={Dash}/>
      <NotFoundRoute handler={BadRoute}/>
    </Route>
  );
})();

Router.run(routes, Router.HistoryLocation, function(Handler) {
  React.render(<Handler/>, document.body);
});
