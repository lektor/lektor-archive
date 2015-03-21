'use strict';

var qs = require('querystring');
var React = require('react');
var Router = require('react-router');

var RecordState = require('../mixins/RecordState');
var utils = require('../utils');
var widgets = require('../widgets');
var {gettext, ngettext} = utils;


function getGoodDefaultModel(models) {
  if (models.page !== undefined) {
    return 'page';
  }
  var choices = Object.keys(models);
  choices.sort();
  return choices[0];
}


var AddAttachmentPage = React.createClass({
  mixins: [
    RecordState
  ],

  getInitialState: function() {
    return {
      newAttachmentInfo: null,
      currentFiles: [],
      isUploading: false,
      currentProgress: 0
    }
  },

  componentDidMount: function() {
    this.syncDialog();
  },

  componentWillReceiveProps: function(nextProps) {
    this.syncDialog();
  },

  syncDialog: function() {
    utils.loadData('/newattachment', {path: this.getRecordPath()})
      .then(function(resp) {
        this.setState({
          newAttachmentInfo: resp
        });
      }.bind(this));
  },

  uploadFile: function(event) {
    this.refs.file.getDOMNode().click();
  },

  onUploadProgress: function(event) {
    var newProgress = Math.round((event.loaded * 100) / event.total);
    if (newProgress != this.state.currentProgress) {
      this.setState({
        currentProgress: newProgress
      });
    }
  },

  onUploadComplete: function(resp, event) {
    this.setState({
      isUploading: false,
      newProgress: 100
    });
  },

  onFileSelected: function(event) {
    if (this.state.isUploading) {
      return;
    }

    var files = this.refs.file.getDOMNode().files;
    this.setState({
      currentFiles: Array.prototype.slice.call(files, 0),
      isUploading: true
    });

    var formData = new FormData();
    formData.append('path', this.getRecordPath());

    for (var i = 0; i < files.length; i++) {
      formData.append('file', files[i], files[i].name);
    }

    var xhr = new XMLHttpRequest();
    xhr.open('POST', utils.getApiUrl('/newattachment'));
    xhr.onload = function(event) {
      this.onUploadComplete(JSON.parse(xhr.responseText), event);
    }.bind(this);
    xhr.upload.onprogress = function(event) {
      this.onUploadProgress(event);
    }.bind(this);
    xhr.send(formData);
  },

  renderCurrentFiles: function() {
    var files = this.state.currentFiles.map(function(file) {
      console.log(file);
      return (
        <li key={file.name}>{file.name} ({file.type})</li>
      );
    });
    return <ul>{files}</ul>;
  },

  render: function() {
    var nai = this.state.newAttachmentInfo;

    if (!nai) {
      return null;
    }

    return (
      <div>
        <h2>{gettext('Add Attachment to “%s”').replace(
          '%s', nai.label)}</h2>
        <p>{gettext('You can upload a new attachment here.')}</p>
        {this.renderCurrentFiles()}
        <p>Progress: {this.state.currentProgress}%</p>
        <input type="file" ref="file" multiple={true}
          style={{display: 'none'}} onChange={this.onFileSelected} />
        <div className="actions">
          <button className="btn btn-primary" onClick={this.uploadFile}>{
            gettext('Upload')}</button>
        </div>
      </div>
    );
  }
});

module.exports = AddAttachmentPage;