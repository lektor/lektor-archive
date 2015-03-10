'use strict';

var React = require('react');
var Router = require("react-router");
var {Route, DefaultRoute, NotFoundRoute} = Router;

// polyfill for internet explorer
require('native-promise-only');

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
  var DeletePage = require('./views/DeletePage');
  var PreviewPage = require('./views/PreviewPage');

  // route setup
  return (
    <Route name="dash" path={$LEKTOR_CONFIG.admin_root} handler={App}>
      <Route name="edit" path=":path/edit" handler={EditPage}/>
      <Route name="delete" path=":path/delete" handler={DeletePage}/>
      <Route name="preview" path=":path/preview" handler={PreviewPage}/>
      <DefaultRoute handler={Dash}/>
      <NotFoundRoute handler={BadRoute}/>
    </Route>
  );
})();

Router.run(routes, Router.HistoryLocation, function(Handler) {
  React.render(<Handler/>, document.body);
});
