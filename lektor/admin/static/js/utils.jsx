var Promise = require('bluebird');


module.exports = {
  loadData: function(url, params) {
    return new Promise(function(resolve, reject) {
      jQuery.ajax({
        url: $LEKTOR_CONFIG.admin_root + '/api' + url,
        data: params
      })
        .done(function(data) {
          resolve(data);
        })
        .fail(function() {
          reject(new Error('Loading of data failed'));
        });
    });
  },

  fsToUrlPath: function(fsPath) {
    var segments = fsPath.match(/^\/*(.*?)\/*$/)[1].split('/');
    if (segments.length == 1 && segments[0] == '') {
      segments = [];
    }
    segments.unshift('root');
    return segments.join(':');
  },

  urlToFsPath: function(urlPath) {
    var segments = urlPath.match(/^:*(.*?):*$/)[1].split(':');
    if (segments.length < 1 || segments[0] != 'root') {
      return null;
    }
    segments[0] = '';
    return segments.join('/');
  },

  urlPathToSegments: function(urlPath) {
    if (!urlPath) {
      return null;
    }
    var rv = urlPath.match(/^:*(.*?):*$/)[1].split('/');
    if (rv.length >= 1 && rv[0] == 'root') {
      return rv.slice(1);
    }
    return null;
  },

  gettext: function(string) {
    return string;
  }
};
