'use strict';

var qs = require('querystring');
var React = require('react');
var Router = require('react-router');

var RecordComponent = require('../components/RecordComponent');
var hub = require('../hub');
var {AttachmentsChangedEvent} = require('../events');
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


class AddAttachmentPage extends RecordComponent {

  constructor() {
    super();
    this.state = {
      newAttachmentInfo: null,
      currentFiles: [],
      isUploading: false,
      currentProgress: 0
    }
  }

  componentDidMount() {
    this.syncDialog();
  }

  componentWillReceiveProps(nextProps) {
    this.syncDialog();
  }

  syncDialog() {
    utils.loadData('/newattachment', {path: this.getRecordPath()})
      .then((resp) => {
        this.setState({
          newAttachmentInfo: resp
        });
      });
  }

  uploadFile(event) {
    React.findDOMNode(this.refs.file).click();
  }

  onUploadProgress(event) {
    var newProgress = Math.round((event.loaded * 100) / event.total);
    if (newProgress != this.state.currentProgress) {
      this.setState({
        currentProgress: newProgress
      });
    }
  }

  onUploadComplete(resp, event) {
    this.setState({
      isUploading: false,
      newProgress: 100
    }, () => {
      hub.emit(new AttachmentsChangedEvent({
        recordPath: this.getRecordPath(),
        attachmentsAdded: resp.buckets.map((bucket) => {
          return bucket.stored_filename;
        })
      }));
    });
  }

  onFileSelected(event) {
    if (this.state.isUploading) {
      return;
    }

    var files = React.findDOMNode(this.refs.file).files;
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
    xhr.onload = (event) => {
      this.onUploadComplete(JSON.parse(xhr.responseText), event);
    };
    xhr.upload.onprogress = (event) => {
      this.onUploadProgress(event);
    };
    xhr.send(formData);
  }

  renderCurrentFiles() {
    var files = this.state.currentFiles.map((file) => {
      return (
        <li key={file.name}>{file.name} ({file.type})</li>
      );
    });
    return <ul>{files}</ul>;
  }

  render() {
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
          style={{display: 'none'}} onChange={this.onFileSelected.bind(this)} />
        <div className="actions">
          <button className="btn btn-primary" onClick={this.uploadFile.bind(this)}>{
            gettext('Upload')}</button>
        </div>
      </div>
    );
  }
}

module.exports = AddAttachmentPage;
