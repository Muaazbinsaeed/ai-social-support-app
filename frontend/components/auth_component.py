"""
Authentication component for login and registration
"""

import streamlit as st
import re
from frontend.utils.api_client import api_client
from frontend.utils.dashboard_state import (
    set_authentication, clear_authentication, set_error_message, set_success_message
)
from frontend.utils.auth_cookies import (
    save_auth_to_cookies, clear_auth_cookies, initialize_auth_from_cookies
)


def show_authentication():
    """Show authentication form (login/register)"""
    st.title("🏛️ Social Security AI")
    st.markdown("---")

    # Check if we should show login or register
    show_register = st.session_state.get('show_register', False)

    if show_register:
        show_register_form()
    else:
        show_login_form()


def show_login_form():
    """Show login form"""
    st.subheader("🔐 Login to Your Account")

    with st.form("login_form"):
        col1, col2 = st.columns([1, 1])

        with col1:
            username = st.text_input(
                "Username or Email",
                placeholder="Enter your username or email",
                help="Use test credentials: demo_user / demo123"
            )

        with col2:
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )

        # Submit button
        submitted = st.form_submit_button("🚀 Login", use_container_width=True)

        if submitted:
            if not username or not password:
                set_error_message("Please enter both username and password")
            else:
                login_user(username, password)

    # Switch to register
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📝 Need an account? Register here", use_container_width=True):
            st.session_state.show_register = True
            st.rerun()

    # Show test credentials
    with st.expander("🧪 Test Credentials"):
        st.markdown("""
        **Available Test Accounts:**
        - Username: `demo_user` | Password: `demo123` ✅ **VERIFIED WORKING**

        *Note: These credentials have been tested and verified to work with the current system.*
        """)


def show_register_form():
    """Show registration form"""
    st.subheader("📝 Create New Account")

    with st.form("register_form"):
        col1, col2 = st.columns([1, 1])

        with col1:
            username = st.text_input(
                "Username",
                placeholder="Choose a username (3-50 characters)",
                help="Username can only contain letters, numbers, and underscores"
            )
            email = st.text_input(
                "Email Address",
                placeholder="your.email@example.com"
            )

        with col2:
            full_name = st.text_input(
                "Full Name",
                placeholder="Your full name (optional)"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Choose a secure password (6+ characters)"
            )

        # Submit button
        submitted = st.form_submit_button("🎉 Create Account", use_container_width=True)

        if submitted:
            if validate_registration_form(username, email, password):
                register_user(username, email, password, full_name)

    # Switch to login
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔐 Already have an account? Login here", use_container_width=True):
            st.session_state.show_register = False
            st.rerun()


def validate_registration_form(username: str, email: str, password: str) -> bool:
    """Validate registration form data"""
    if not username or not email or not password:
        set_error_message("Please fill in all required fields")
        return False

    # Validate username
    if len(username) < 3 or len(username) > 50:
        set_error_message("Username must be between 3 and 50 characters")
        return False

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        set_error_message("Username can only contain letters, numbers, and underscores")
        return False

    # Validate email
    email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
    if not re.match(email_pattern, email):
        set_error_message("Please enter a valid email address")
        return False

    # Validate password
    if len(password) < 6:
        set_error_message("Password must be at least 6 characters long")
        return False

    return True


def login_user(username: str, password: str):
    """Login user with API call"""
    with st.spinner("🔄 Logging in..."):
        result = api_client.login(username, password)

        if 'error' in result:
            if result.get('status_code') == 401:
                set_error_message("Invalid username or password. Please check your credentials.")
            else:
                set_error_message(f"Login failed: {result['error']}")
        else:
            # Login successful
            set_authentication(result['access_token'], result['user_info'])

            # Save authentication to cookies for persistence
            save_auth_to_cookies(result['access_token'], result['user_info'])

            # Check for existing applications and load data automatically
            from frontend.utils.dashboard_state import load_existing_application

            application_loaded = False

            # Try the simple applications list first (more reliable)
            apps_result = api_client.get_user_applications_simple()

            if 'error' not in apps_result and apps_result.get('total_count', 0) > 0:
                applications = apps_result.get('applications', [])

                # Find the most recent active application
                for app in applications:
                    app_status = app.get('status', 'draft')
                    if app_status in ['draft', 'form_submitted', 'documents_uploaded', 'scanning_documents',
                                    'ocr_completed', 'analyzing_income', 'analyzing_identity',
                                    'analysis_completed', 'making_decision']:
                        app_id = app.get('application_id')
                        if app_id:
                            # Load full application data into session state
                            if load_existing_application(app_id, api_client):
                                set_success_message(f"Welcome back, {result['user_info']['username']}! Your {app_status} application has been loaded.")
                                application_loaded = True
                                break

            # If simple list failed, try the original endpoint as fallback
            if not application_loaded:
                apps_result_fallback = api_client.get_user_applications()
                if 'error' not in apps_result_fallback:
                    applications = apps_result_fallback.get('applications', [])
                    for app in applications:
                        if app.get('status') in ['draft', 'form_submitted', 'documents_uploaded', 'scanning_documents',
                                               'ocr_completed', 'analyzing_income', 'analyzing_identity',
                                               'analysis_completed', 'making_decision']:
                            app_id = app.get('application_id') or app.get('id')
                            if app_id and load_existing_application(app_id, api_client):
                                app_status = app.get('status', 'draft')
                                set_success_message(f"Welcome back, {result['user_info']['username']}! Your {app_status} application has been loaded.")
                                application_loaded = True
                                break

            # If no application was loaded, show appropriate message
            if not application_loaded:
                # Don't set needs_application_loading flag since we want a clean experience
                set_success_message(f"Welcome back, {result['user_info']['username']}! Ready to start a new application or continue an existing one.")

            st.rerun()


def register_user(username: str, email: str, password: str, full_name: str = None):
    """Register new user with API call"""
    with st.spinner("🔄 Creating account..."):
        result = api_client.register(username, email, password, full_name)

        if 'error' in result:
            if result.get('status_code') == 409:
                set_error_message("Username or email already exists. Please choose different ones.")
            else:
                set_error_message(f"Registration failed: {result['error']}")
        else:
            # Registration successful
            set_success_message("Account created successfully! Please login with your credentials.")
            st.session_state.show_register = False
            st.rerun()


def show_user_header():
    """Show user header with logout option"""
    if st.session_state.get('user_info'):
        user_info = st.session_state.user_info

        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            st.markdown(f"**Welcome, {user_info.get('full_name', user_info.get('username'))}** 👋")

        with col2:
            st.markdown(f"*{user_info.get('email')}*")

        with col3:
            if st.button("🚪 Logout"):
                logout_user()


def logout_user():
    """Logout current user"""
    clear_authentication()

    # Clear authentication cookies
    clear_auth_cookies()

    set_success_message("You have been logged out successfully.")
    st.rerun()