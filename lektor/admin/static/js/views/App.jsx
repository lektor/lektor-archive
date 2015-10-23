'use strict';

var React = require('react');
var Router = require("react-router");
var {RouteHandler} = Router;

var BreadCrumbs = require('../components/BreadCrumbs');
var Sidebar = require('../components/Sidebar');
var Component = require('../components/Component');
var dialogSystem = require('../dialogSystem');
var {DialogChangedEvent} = require('../events');
var hub = require('../hub');


class App extends Component {

  constructor(props) {
    super(props);
    this.state = {
      currentDialog: null
    };
    this.onDialogChanged = this.onDialogChanged.bind(this);
  }

  componentDidMount() {
    super();
    hub.subscribe(DialogChangedEvent, this.onDialogChanged);
  }

  componentWillUnmount() {
    super();
    hub.unsubscribe(DialogChangedEvent, this.onDialogChanged);
  }

  onDialogChanged(event) {
    this.setState({
      currentDialog: event.currentDialog
    });
  }

  render() {
    // the current dialog is managed from within the application and sent
    // back into the dialog system.  This makes the app the owner of the
    // dialog and much easier to deal with.  The dialog system itself then
    // only needs to exchange messages with the app to update the dialogs.
    var dialog = null;
    if (this.state.currentDialog) {
      dialog = <this.state.currentDialog ref={(ref) =>
        dialogSystem.notifyDialogInstance(ref)} />;
    } else {
      dialogSystem.notifyDialogInstance(null);
    }

    var className = 'application';
    if (dialog !== null) {
      className += ' protector-open';
    }

    return (
      <div className={className}>
        <header>
          <BreadCrumbs>
            <button type="button" className="navbar-toggle"
                data-toggle="offcanvas"
                data-target=".sidebar-block">
              <span className="sr-only">Toggle navigation</span>
              <span className="icon-list"></span>
              <span className="icon-list"></span>
              <span className="icon-list"></span>
            </button>
          </BreadCrumbs>
        </header>
        {dialog}
        <div className="editor container">
          <div className="interface-protector"></div>
          <div className="sidebar-block block-offcanvas block-offcanvas-left">
            <nav className="sidebar col-md-2 col-sm-3 sidebar-offcanvas">
              <Sidebar/>
            </nav>
            <div className="view col-md-10 col-sm-9">
              <RouteHandler/>
            </div>
          </div>
        </div>
      </div>
    );
  }
}

module.exports = App;
