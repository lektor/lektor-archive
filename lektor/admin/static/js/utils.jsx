var utils = {
  getCanonicalUrl: function(localPath) {
    return $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1] +
      '/' + utils.stripLeadingSlash(localPath);
  },

  isValidUrl: function(url) {
    return !!url.match(/^(https?|ftp):\/\/\S+$/);
  },

  stripLeadingSlash: function(string) {
    return string.match(/^\/*(.*?)$/)[1];
  },

  stripTrailingSlash: function(string) {
    return string.match(/^(.*?)\/*$/)[1];
  },

  flipSetValue: function(originalSet, value, isActive) {
    if (isActive) {
      return utils.addToSet(originalSet, value);
    } else {
      return utils.removeFromSet(originalSet, value);
    }
  },

  addToSet: function(originalSet, value) {
    for (var i = 0; i < originalSet.length; i++) {
      if (originalSet[i] === value) {
        return originalSet;
      }
    }
    var rv = originalSet.slice();
    rv.push(value);
    return rv;
  },

  removeFromSet: function(originalSet, value) {
    var rv = null;
    var off = 0;
    for (var i = 0; i < originalSet.length; i++) {
      if (originalSet[i] === value) {
        if (rv === null) {
          rv = originalSet.slice();
        }
        rv.splice(i - (off++), 1);
      }
    }
    return (rv === null) ? originalSet : rv;
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
