'use strict';

var React = require('react');
var Component = require('../components/Component');


class Dash extends Component {

  componentDidMount() {
    super();
    this.context.router.transitionTo('preview', {'path': 'root'});
  }

  render() {
    return null;
  }
}

Dash.contextTypes = {
  router: React.PropTypes.any.isRequired
};

module.exports = Dash;
