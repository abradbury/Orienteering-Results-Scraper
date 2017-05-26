"use strict";

// This is a controlller view

var React = require('react');
var Router = require('react-router');
var toastr = require('toastr');
var AuthorForm = require('./authorForm');
var AuthorActions = require('../../actions/authorActions');
var AuthorStore = require('../../stores/authorStore');
var browserHistory = Router.browserHistory;
var withRouter = Router.withRouter;

var ManageAuthorPage = React.createClass({
    componentDidMount: function () {
        this.props.router.setRouteLeaveHook(this.props.route, this.routerWillLeave);
    },

    routerWillLeave: function (nextLocation) {
        // Return false to prevent a transition w/o prompting the user,
        // or return a string to allow the user to decide:
        if (this.state.unsavedWork) {
            return 'Leave without saving?';
        }
        return true;
    },

    getInitialState: function () {
        return {
            author: { id: '', firstName: '', lastName: '' },
            errors: {},
            unsavedWork: false
        };
    },

    // Using componentWillMount instead of componentDidMount because
    // calling setState here does not lead to a re-render
    componentWillMount: function () {
        var authorId = this.props.params.id; //from the path '/author:id'
        if (authorId) {
            this.setState({ author: AuthorStore.getAuthorById(authorId) });
        }

        // If making an asynchronous call (often the case) will need to 
        // handle asynchrony via callback or promise
    },

    setAuthorState: function (event) {
        this.setState({ unsavedWork: true });
        var field = event.target.name;
        var value = event.target.value;
        this.state.author[field] = value;
        return this.setState({ author: this.state.author });
    },

    authorFormIsValid: function () {
        var formIsValid = true;
        this.state.errors = {}; // Clear previous errors

        if (this.state.author.firstName < 3) {
            this.state.errors.firstName = 'First name must be at least 3 characters';
            formIsValid = false;
        }

        if (this.state.author.lastName < 3) {
            this.state.errors.lastName = 'Last name must be at least 3 characters';
            formIsValid = false;
        }

        this.setState({ errors: this.state.errors });
        return formIsValid;
    },

    saveAuthor: function (event) {
        event.preventDefault();

        if (!this.authorFormIsValid()) {
            return;
        }

        if (this.state.author.id) {
            AuthorActions.updateAuthor(this.state.author);
        } else {
            AuthorActions.createAuthor(this.state.author);
        }

        this.setState({ unsavedWork: false });
        toastr.success("Author saved");
        browserHistory.push('/authors');
    },

    render: function () {
        return (
            <AuthorForm
                author={this.state.author}
                onChange={this.setAuthorState}
                onSave={this.saveAuthor}
                errors={this.state.errors} />
        );
    }
});

// Using withRouter higher order component to wrap ManageAuthorPage
// to notify the user when attempting to navigate away when the form is dirty.
module.exports = withRouter(ManageAuthorPage);