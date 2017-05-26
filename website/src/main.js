"use strict";

// Entry point for application
// const not in ES5... :(

// FIXME: Leave page warning when completing form - remove
// TODO: Move away from React.createClass (depricated)
// TODO: Move from ES5 to ES6
// TODO: Connect to MongoDB

var React = require('react');
var ReactDOM = require('react-dom');
var routes = require('./routes');
var InitialiseActions = require('./actions/initialiseActions');

InitialiseActions.initApp();

ReactDOM.render(routes, document.getElementById('app'));
