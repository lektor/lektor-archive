var lektor = {
  cleanupPath: function(path) {
    return path.match(/^\/*(.*?)\/*$/)[1];
  },

  getSourcePath: function() {
    return lektor.cleanupPath(window.location.pathname.split('!')[0]);
  },

  syncNavigation: function(frm) {
    var path = lektor.cleanupPath(frm.contentWindow.location.pathname);
    var sourcePath = lektor.getSourcePath();

    if (path != sourcePath) {
      window.location.href = '/' + path + '!/';
    }
  }
};

$(function() {
  var frm = $('div.preview iframe');
  frm.on('load', function() {
    lektor.syncNavigation(this);
  });
});
