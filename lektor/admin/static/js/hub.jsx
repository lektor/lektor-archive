'use strict';

var React = require('react');


class Hub {

  constructor() {
    this._subscriptions = {};
  }

  /* subscribes a callback to an event */
  subscribe(event, callback, thisArg) {
    thisArg = thisArg || null;

    if (typeof event !== 'string') {
      event = event.getEventType();
    }

    var subs = this._subscriptions[event];
    if (subs === undefined) {
      this._subscriptions[event] = subs = [];
    }

    for (var i = 0; i < subs.length; i++) {
      if (subs[i][0] === callback && subs[i][1] === thisArg) {
        return false;
      }
    }

    subs.push([callback, thisArg]);
    return true;
  }

  /* unsubscribes a callback from an event */
  unsubscribe(event, callback, thisArg) {
    thisArg = thisArg || null;

    if (typeof event !== 'string') {
      event = event.getEventType();
    }

    var subs = this._subscriptions[event];
    if (subs === undefined) {
      return false;
    }

    for (var i = 0; i < subs.length; i++) {
      if (subs[i][0] === callback && subs[i][1] === thisArg) {
        subs.splice(i, 1);
        return true;
      }
    }
    return false;
  }

  /* emits an event with some parameters */
  emit(event) {
    var subs = this._subscriptions[event.type];
    if (subs !== undefined) {
      subs.forEach(function(obj) {
        var [callback, thisArg] = obj;
        try {
          callback.call(thisArg, event);
        } catch (e) {
          console.log('Event callback failed: ', e, 'callback=',
                      callback, 'event=', event);
        }
      })
    }
  }
}


var hub = new Hub();


module.exports = hub;
