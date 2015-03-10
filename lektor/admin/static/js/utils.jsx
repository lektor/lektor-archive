var utils = {
  getCanonicalUrl: function(localPath) {
    return $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1] +
      '/' + utils.stripLeadingSlash(localPath);
  },

  stripLeadingSlash: function(string) {
    return string.match(/^\/*(.*?)$/)[1];
  },

  stripTrailingSlash: function(string) {
    return string.match(/^(.*?)\/*$/)[1];
  },

  urlPathsConsideredEqual: function(a, b) {
    if ((a == null) || (b == null)) {
      return false;
    }
    return utils.stripTrailingSlash(a) == utils.stripTrailingSlash(b);
  },

  fsPathFromAdminObservedPath: function(adminPath) {
    var base = $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1];
    if (adminPath.substr(0, base.length) != base) {
      return null;
    }
    return '/' + adminPath.substr(base.length).match(/^\/*(.*?)\/*$/)[1];
  },

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

module.exports = utils;
