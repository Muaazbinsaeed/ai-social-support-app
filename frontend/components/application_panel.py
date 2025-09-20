"""
Application form panel component
"""

import streamlit as st
import re
from frontend.utils.api_client import api_client
from frontend.utils.dashboard_state import (
    update_form_data, get_form_data, set_current_application,
    set_error_message, set_success_message, reset_application_state
)


def show_application_panel():
    """Show the application form panel (left panel)"""
    st.subheader("📋 Application Form")

    # Check if there's an active application
    current_app_id = st.session_state.get('current_application_id')

    if current_app_id:
        show_application_status_summary()
    else:
        show_application_form()


def show_application_form():
    """Show the application form"""
    with st.form("application_form", clear_on_submit=False):
        st.markdown("**Personal Information**")

        # Full Name
        full_name = st.text_input(
            "Full Name *",
            value=get_form_data('full_name', ''),
            placeholder="Enter your full name",
            help="Enter your full name as shown on official documents",
            key="form_full_name"
        )

        # Emirates ID
        emirates_id = st.text_input(
            "Emirates ID *",
            value=get_form_data('emirates_id', ''),
            placeholder="784-YYYY-XXXXXXX-X",
            help="Format: 784-YYYY-XXXXXXX-X (e.g., 784-1990-1234567-8)",
            key="form_emirates_id"
        )

        # Phone Number
        phone = st.text_input(
            "Phone Number *",
            value=get_form_data('phone', ''),
            placeholder="+971XXXXXXXXX or 05XXXXXXXX",
            help="UAE phone number format",
            key="form_phone"
        )

        # Email Address
        email = st.text_input(
            "Email Address *",
            value=get_form_data('email', ''),
            placeholder="your.email@example.com",
            help="Valid email address for communication",
            key="form_email"
        )

        st.markdown("---")

        # Form buttons
        col1, col2 = st.columns(2)

        with col1:
            save_draft = st.form_submit_button(
                "💾 Save Draft",
                help="Save your progress without submitting",
                use_container_width=True
            )

        with col2:
            submit_form = st.form_submit_button(
                "🚀 Submit Application",
                help="Submit your application for processing",
                use_container_width=True,
                type="primary"
            )

        if save_draft or submit_form:
            if validate_form_data(full_name, emirates_id, phone, email, submit_form):
                # Save form data to session state
                update_form_data('full_name', full_name)
                update_form_data('emirates_id', emirates_id)
                update_form_data('phone', phone)
                update_form_data('email', email)

                if save_draft:
                    set_success_message("✅ Draft saved successfully!")
                    st.rerun()
                elif submit_form:
                    submit_application(full_name, emirates_id, phone, email)

    # Show example data
    with st.expander("📝 Example Data"):
        st.markdown("""
        **Sample Information:**
        - **Full Name:** Ahmed Ali Hassan
        - **Emirates ID:** 784-1990-1234567-8
        - **Phone:** +971501234567
        - **Email:** ahmed@example.com
        """)


def show_application_status_summary():
    """Show application status summary when application exists"""
    st.info("📋 **Application Submitted**")

    # Show basic application info
    form_data = st.session_state.application_form_data
    if form_data:
        st.markdown(f"**Name:** {form_data.get('full_name', 'N/A')}")
        st.markdown(f"**Emirates ID:** {form_data.get('emirates_id', 'N/A')}")
        st.markdown(f"**Application ID:** `{st.session_state.current_application_id}`")

    st.markdown("---")

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 View Status", use_container_width=True):
            # Scroll to status panel or highlight it
            st.success("👈 Check the Status Panel for detailed progress")

    with col2:
        if st.button("🆕 New Application", use_container_width=True):
            start_new_application()

    # Show tips
    st.markdown("---")
    st.markdown("**Next Steps:**")
    st.markdown("1. Upload your documents in the center panel")
    st.markdown("2. Monitor progress in the status panel")
    st.markdown("3. Receive your decision within 2 minutes")


def validate_form_data(full_name: str, emirates_id: str, phone: str, email: str, is_submit: bool) -> bool:
    """Validate form data"""
    errors = []

    # For submit, all fields are required
    if is_submit:
        if not full_name.strip():
            errors.append("Full name is required")
        if not emirates_id.strip():
            errors.append("Emirates ID is required")
        if not phone.strip():
            errors.append("Phone number is required")
        if not email.strip():
            errors.append("Email address is required")

    # Validate Emirates ID format if provided
    if emirates_id.strip():
        emirates_pattern = r'^784-[0-9]{4}-[0-9]{7}-[0-9]$'
        if not re.match(emirates_pattern, emirates_id):
            errors.append("Invalid Emirates ID format. Use: 784-YYYY-XXXXXXX-X")

    # Validate phone format if provided
    if phone.strip():
        phone_pattern = r'^(\+971|05)[0-9]{8,9}$'
        if not re.match(phone_pattern, phone):
            errors.append("Invalid phone format. Use: +971XXXXXXXXX or 05XXXXXXXX")

    # Validate email format if provided
    if email.strip():
        email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
        if not re.match(email_pattern, email):
            errors.append("Invalid email format")

    # Validate full name format if provided
    if full_name.strip():
        if len(full_name.strip()) < 2:
            errors.append("Full name must be at least 2 characters")
        if not re.match(r'^[a-zA-Z\s]+$', full_name.strip()):
            errors.append("Full name can only contain letters and spaces")

    if errors:
        set_error_message("❌ " + " | ".join(errors))
        return False

    return True


def submit_application(full_name: str, emirates_id: str, phone: str, email: str):
    """Submit application to API"""
    application_data = {
        "full_name": full_name.strip(),
        "emirates_id": emirates_id.strip(),
        "phone": phone.strip(),
        "email": email.strip()
    }

    with st.spinner("🚀 Submitting application..."):
        result = api_client.create_application(application_data)

        if 'error' in result:
            if result.get('status_code') == 409:
                set_error_message("❌ You already have an active application. Please complete it first.")
            else:
                set_error_message(f"❌ Submission failed: {result['error']}")
        else:
            # Application created successfully
            application_id = result.get('application_id')
            set_current_application(application_id)
            set_success_message("🎉 Application submitted successfully! Please upload your documents.")
            st.rerun()


def start_new_application():
    """Start a new application (reset state)"""
    # Confirm with user
    if st.session_state.get('current_application_id'):
        # Show confirmation dialog
        if 'confirm_new_app' not in st.session_state:
            st.session_state.confirm_new_app = False

        if not st.session_state.confirm_new_app:
            st.warning("⚠️ This will discard your current application. Are you sure?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, Start New", key="confirm_yes"):
                    st.session_state.confirm_new_app = True
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", key="confirm_no"):
                    st.stop()
        else:
            # Confirmed, reset application state
            reset_application_state()
            st.session_state.confirm_new_app = False
            set_success_message("🆕 Ready for new application!")
            st.rerun()
    else:
        # No current application, just reset
        reset_application_state()
        set_success_message("🆕 Ready for new application!")
        st.rerun()