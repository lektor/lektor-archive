var React = require('react');

var utils = require('../utils');
var {gettext} = utils;


function ValidationFailure(options) {
  this.message = options.message || gettext('Invalid input');
  this.type = options.type || 'error';
}


module.exports = {
  ValidationFailure: ValidationFailure
};
