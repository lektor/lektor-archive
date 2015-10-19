'use strict';

var i18n = {
  // XXX: lazy load this somehow
  translations: {
    "en": require('./localization/en.json'),
    "de": require('./localization/de.json'),
  },

  currentLanguage: 'en',

  trans: function(key) {
    var rv;
    if (typeof key === 'object') {
      rv = key[i18n.currentLanguage];
      if (rv === undefined) {
        rv = key.en;
      }
      return rv;
    }
    return i18n.translations[i18n.currentLanguage][key] || key;
  }
};


module.exports = i18n;
