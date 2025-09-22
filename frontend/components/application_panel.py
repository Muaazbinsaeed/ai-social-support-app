"""
Application form panel component - Simplified and improved with better state management
"""

import streamlit as st
import re
from datetime import datetime
from frontend.utils.api_client import api_client
from frontend.utils.dashboard_state import (
    update_form_data, get_form_data, set_current_application,
    reset_application_state, load_existing_application
)


def show_application_panel():
    """Show the application form panel - One application per user"""
    st.subheader("📋 Your Application Form")

    # Show any messages
    if 'app_message' in st.session_state:
        msg = st.session_state.app_message
        if msg['type'] == 'success':
            st.success(msg['content'])
        elif msg['type'] == 'error':
            st.error(msg['content'])
        elif msg['type'] == 'info':
            st.info(msg['content'])
        elif msg['type'] == 'warning':
            st.warning(msg['content'])

        # Auto-clear success/info messages after display
        if msg['type'] in ['success', 'info']:
            del st.session_state.app_message

    # Check for existing application
    current_app_id = st.session_state.get('current_application_id')
    processing_status = st.session_state.get('processing_status') or {}
    current_state = processing_status.get('current_state', 'draft')

    # Show status badge with edit capability indicator
    if current_app_id:
        show_status_badge(current_state, processing_status.get('progress', 0))

    # Single application form - either new or existing
    if current_app_id:
        show_application_form(is_existing=True, application_id=current_app_id, current_state=current_state)
    else:
        show_application_form(is_existing=False)


def search_user_applications():
    """Search for user's applications using multiple methods"""
    try:
        # Method 1: Try the applications list endpoint
        apps_result = api_client.get_user_applications()
        if 'error' not in apps_result:
            applications = apps_result.get('applications', [])
            # Find the most recent active application
            for app in applications:
                if app.get('status') in ['draft', 'form_submitted', 'documents_uploaded', 'scanning_documents',
                                       'ocr_completed', 'analyzing_income', 'analyzing_identity',
                                       'analysis_completed', 'making_decision']:
                    app_id = app.get('application_id') or app.get('id')
                    if app_id and load_existing_application(app_id, api_client):
                        return app_id

        # Method 2: Try to get the current user info and search by common patterns
        # This is a fallback method - in a real system you might have other ways to find applications
        user_info = st.session_state.get('user_info', {})
        if user_info:
            # For now, we'll return None since we need the specific application ID
            # In a production system, you might have additional search endpoints
            pass

        return None

    except Exception as e:
        # Log the error but don't show it to user
        return None


def show_manual_loading_option():
    """Show manual application loading option"""
    st.warning("⚠️ **Application auto-loading failed.** Please load your existing application manually.")

    # Show helpful instructions
    with st.expander("📖 How to find your Application ID", expanded=False):
        st.markdown("""
        **Your Application ID was provided when you first created your application.**

        It looks like: `455bbd42-0429-456d-a344-312410c240aa`

        **Where to find it:**
        - Check your email confirmation (if you received one)
        - Look in your browser history for the application ID
        - Contact support with your name and email if needed
        """)

    # Application ID input
    app_id_input = st.text_input(
        "🆔 Enter your Application ID",
        placeholder="e.g., 455bbd42-0429-456d-a344-312410c240aa",
        help="Enter the full application ID you received when creating your application"
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        load_btn = st.button("📋 Load My Application", use_container_width=True, type="primary", disabled=not app_id_input.strip())

    with col2:
        auto_search_btn = st.button("🔍 Auto Search", use_container_width=True, help="Try to automatically find your applications")

    if load_btn and app_id_input.strip():
        # Validate application ID format (basic UUID format check)
        app_id = app_id_input.strip()
        if len(app_id) < 20:  # Basic length check
            show_message("❌ Application ID seems too short. Please check and try again.", "error")
        else:
            with st.spinner("🔄 Loading your application..."):
                if load_existing_application(app_id, api_client):
                    st.session_state.needs_application_loading = False
                    show_message("✅ Application loaded successfully!", "success")
                    st.rerun()
                else:
                    show_message("❌ Could not load application. Please verify the ID is correct.", "error")

    if auto_search_btn:
        # Try to find user's applications automatically
        with st.spinner("🔍 Searching for your applications..."):
            found_application = search_user_applications()

        if found_application:
            st.session_state.needs_application_loading = False
            show_message(f"✅ Found and loaded your application ({found_application[:8]}...)!", "success")
            st.rerun()
        else:
            show_message("❌ Auto-search failed. Please enter your application ID manually above.", "warning")

    st.markdown("---")


def show_status_badge(current_state: str, progress: int):
    """Show application status badge"""
    if not current_state or current_state == 'draft':
        return

    # Map states to user-friendly labels and colors
    state_info = {
        'draft': ('Draft', '🔄', 'info'),
        'form_submitted': ('Form Submitted', '✅', 'success'),
        'documents_uploaded': ('Documents Uploaded', '📄', 'success'),
        'scanning_documents': ('Scanning Documents', '🔍', 'warning'),
        'ocr_completed': ('Documents Processed', '✅', 'success'),
        'analyzing_income': ('Analyzing Income', '💰', 'warning'),
        'analyzing_identity': ('Verifying Identity', '🆔', 'warning'),
        'analysis_completed': ('Analysis Complete', '✅', 'success'),
        'making_decision': ('Making Decision', '⚖️', 'warning'),
        'decision_completed': ('Decision Complete', '✅', 'success'),
        'approved': ('Approved', '🎉', 'success'),
        'rejected': ('Rejected', '❌', 'error'),
        'needs_review': ('Under Review', '👥', 'info')
    }

    label, icon, color = state_info.get(current_state, ('Unknown', '❓', 'info'))

    # Show status with progress and editability indicator
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if color == 'success':
            st.success(f"{icon} Status: {label}")
        elif color == 'warning':
            st.warning(f"{icon} Status: {label}")
        elif color == 'error':
            st.error(f"{icon} Status: {label}")
        else:
            st.info(f"{icon} Status: {label}")

    with col2:
        if progress > 0:
            st.metric("Progress", f"{progress}%")

    with col3:
        # Show editability indicator
        if current_state in ['draft', 'form_submitted', 'documents_uploaded']:
            st.success("✏️ **Editable**")
        else:
            st.warning("🔒 **Read-only**")
            if current_state in ['scanning_documents', 'ocr_completed', 'analyzing_income', 'analyzing_identity', 'making_decision', 'analysis_completed']:
                st.caption("💡 Reset to edit")

    # Show progress bar for active processing
    if current_state in ['scanning_documents', 'analyzing_income', 'analyzing_identity', 'making_decision'] and progress > 0:
        st.progress(progress / 100)


def show_application_form(is_existing: bool = False, application_id: str = None, current_state: str = 'draft'):
    """Show application form - unified for new and existing applications"""

    if is_existing:
        st.success(f"📝 **Editing Your Application:** {application_id[:8] if application_id else 'Unknown'}...")

        # Show last updated info
        processing_status = st.session_state.get('processing_status') or {}
        last_updated = processing_status.get('last_updated')
        if last_updated:
            st.caption(f"Last updated: {last_updated}")

        # Show action buttons for existing application
        show_application_actions(application_id, current_state)
    else:
        st.info("📝 **New Application** - Fill out your information to start your social security benefit application.")
        
        # Show simplified action buttons for new applications
        show_new_application_actions()

    # Determine if form should be editable
    # Allow editing only in early stages (match backend restrictions)
    is_editable = current_state in ['draft', 'form_submitted', 'documents_uploaded']

    # Always show the form (editable or read-only)
    if not is_editable and is_existing:
        # Show specific message based on current state
        if current_state in ['scanning_documents', 'ocr_completed']:
            st.info("🔍 **Document Processing Active** - Your application form is temporarily read-only while we scan and extract text from your documents. Form editing will be available again after processing completes.")
        elif current_state in ['analyzing_income', 'analyzing_identity']:
            st.info("🤖 **AI Analysis in Progress** - Your application form is read-only while our AI analyzes your documents. This ensures data consistency during processing.")
        elif current_state in ['making_decision', 'analysis_completed']:
            st.info("⚖️ **Decision Processing** - Your application form is finalized and under review. No further changes are allowed.")
        elif current_state in ['approved', 'rejected', 'needs_review']:
            st.success("✅ **Application Complete** - Your application has been processed. Form data is shown for reference only.")
        else:
            st.warning("⚠️ **Application is in advanced processing.** Form data is shown for reference only.")

        show_readonly_form()
    else:
        # Show editable form
        show_editable_form(is_existing, application_id)


def show_editable_form(is_existing: bool, application_id: str = None):
    """Show the editable form"""
    # Show the form - don't clear on submit to preserve values
    with st.form("application_form", clear_on_submit=False):
        st.markdown("**Personal Information**")

        # Get current form data - force refresh from session state
        current_full_name = get_form_data('full_name', '')
        current_emirates_id = get_form_data('emirates_id', '')
        current_phone = get_form_data('phone', '')
        current_email = get_form_data('email', '')
        
        # Store original values to detect changes
        if 'original_form_data' not in st.session_state:
            st.session_state.original_form_data = {
                'full_name': current_full_name,
                'emirates_id': current_emirates_id,
                'phone': current_phone,
                'email': current_email
            }

        # Use static keys to avoid caching issues - let Streamlit handle state naturally
        form_key = "edit_form" if is_existing else "new_form"

        # Form fields - remove dynamic keys that cause caching issues
        full_name = st.text_input(
            "Full Name *",
            value=current_full_name,
            placeholder="Enter your full name",
            help="Enter your full name as shown on official documents",
            key=f"full_name_{form_key}"
        )

        emirates_id = st.text_input(
            "Emirates ID *",
            value=current_emirates_id,
            placeholder="784-YYYY-XXXXXXX-X",
            help="Format: 784-YYYY-XXXXXXX-X (e.g., 784-1985-9876543-2)",
            key=f"emirates_id_{form_key}"
        )

        phone = st.text_input(
            "Phone Number *",
            value=current_phone,
            placeholder="+971XXXXXXXXX or 05XXXXXXXX",
            help="UAE phone number format",
            key=f"phone_{form_key}"
        )

        email = st.text_input(
            "Email Address *",
            value=current_email,
            placeholder="your.email@example.com",
            help="Valid email address for communication",
            key=f"email_{form_key}"
        )

        st.markdown("---")

        # Form buttons
        col1, col2 = st.columns(2)

        with col1:
            save_draft = st.form_submit_button(
                "💾 Save Draft",
                help="Save your progress",
                use_container_width=True
            )

        with col2:
            if is_existing:
                submit_form = st.form_submit_button(
                    "🔄 Update Application",
                    help="Update your application",
                    use_container_width=True,
                    type="primary"
                )
            else:
                submit_form = st.form_submit_button(
                    "🚀 Submit Application",
                    help="Submit your application for processing",
                    use_container_width=True,
                    type="primary"
                )

        # Handle form submission
        if save_draft or submit_form:
            if is_existing:
                handle_form_update(application_id, full_name, emirates_id, phone, email, submit_form)
            else:
                handle_new_application(full_name, emirates_id, phone, email, submit_form)

    # Show example data for new applications
    if not is_existing:
        with st.expander("📝 Example Data"):
            st.markdown("""
            **Sample Information:**
            - **Full Name:** Ahmed Ali Hassan
            - **Emirates ID:** 784-1985-9876543-2
            - **Phone:** +971501234567
            - **Email:** ahmed@example.com
            """)


def show_readonly_form():
    """Show form data in readonly mode"""
    st.markdown("**Current Application Information:**")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Full Name", value=get_form_data('full_name', 'Not provided'), disabled=True)
        st.text_input("Emirates ID", value=get_form_data('emirates_id', 'Not provided'), disabled=True)

    with col2:
        st.text_input("Phone Number", value=get_form_data('phone', 'Not provided'), disabled=True)
        st.text_input("Email Address", value=get_form_data('email', 'Not provided'), disabled=True)


def show_new_application_actions():
    """Show action buttons for new applications"""
    st.markdown("**Quick Actions:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Clear form button for new applications
        if st.button("🔄 Clear Form", use_container_width=True, key="clear_form_btn", help="Clear all form fields"):
            # Clear form data
            st.session_state.application_form_data = {}
            # Clear widget states
            form_keys = ['full_name_new_form', 'emirates_id_new_form', 'phone_new_form', 'email_new_form']
            for key in form_keys:
                if key in st.session_state:
                    del st.session_state[key]
            show_message("✅ Form cleared! Start fresh.", "info")
            st.rerun()
    
    with col2:
        # Load existing application if user has one
        if st.button("🔍 Find My Application", use_container_width=True, key="find_app_btn", help="Search for existing application"):
            with st.spinner("Searching for your application..."):
                from frontend.utils.api_client import api_client
                apps_result = api_client.get_user_applications()
                if 'error' not in apps_result:
                    applications = apps_result.get('applications', [])
                    if applications:
                        # Load the first active application
                        app = applications[0]
                        app_id = app.get('application_id') or app.get('id')
                        if app_id and load_existing_application(app_id, api_client):
                            show_message("✅ Found your application!", "success")
                            st.rerun()
                        else:
                            show_message("❌ Could not load application", "error")
                    else:
                        show_message("ℹ️ No existing application found. Create a new one!", "info")
                else:
                    show_message("❌ Could not search for applications", "error")


def show_application_actions(application_id: str, current_state: str):
    """Show action buttons for existing applications"""
    st.markdown("**Quick Actions:**")

    col1, col2, col3 = st.columns(3)

    with col1:
        refresh_btn = st.button("🔄 Refresh", use_container_width=True, key="refresh_btn", help="Refresh application data")

    with col2:
        # Show reset button for stuck applications OR to clear and start over
        if current_state in ['scanning_documents', 'ocr_completed', 'analyzing_income', 'analyzing_identity', 'making_decision', 'analysis_completed']:
            reset_btn = st.button("🔧 Reset to Edit", use_container_width=True, key="reset_btn", help="Reset application to editable state")
        else:
            reset_btn = st.button("🆕 Start Over", use_container_width=True, key="start_over_btn", help="Clear application and start fresh")

    with col3:
        # Delete application option for draft states
        if current_state in ['draft', 'form_submitted', 'documents_uploaded']:
            delete_app = st.button("🗑️ Delete", use_container_width=True, type="secondary", key="delete_btn", help="Delete this application")
        else:
            delete_app = False

    # Handle refresh
    if refresh_btn:
        if load_existing_application(application_id, api_client):
            show_message("🔄 Application data refreshed!", "success")
            st.rerun()
        else:
            show_message("❌ Failed to refresh application data", "error")

    # Handle reset/start over
    if reset_btn:
        if current_state in ['scanning_documents', 'ocr_completed', 'analyzing_income', 'analyzing_identity', 'making_decision', 'analysis_completed']:
            # Reset to editable state
            if st.session_state.get('confirm_reset', False):
                with st.spinner("🔄 Resetting application status..."):
                    result = api_client.reset_application_status(application_id)
                    if 'error' in result:
                        show_message(f"❌ Failed to reset: {result['error']}", "error")
                    else:
                        if load_existing_application(application_id, api_client):
                            st.session_state.confirm_reset = False
                            show_message("✅ Application reset! You can now edit the form.", "success")
                            st.rerun()
            else:
                st.session_state.confirm_reset = True
                show_message("⚠️ Click 'Reset to Edit' again to confirm.", "warning")
        else:
            # Start over - clear everything
            if st.session_state.get('confirm_start_over', False):
                # Delete current application
                result = api_client.cancel_application(application_id)
                if 'error' not in result:
                    # Clear all states
                    form_keys = ['full_name_new_form', 'emirates_id_new_form', 'phone_new_form', 'email_new_form',
                               'full_name_edit_form', 'emirates_id_edit_form', 'phone_edit_form', 'email_edit_form']
                    for key in form_keys:
                        if key in st.session_state:
                            del st.session_state[key]
                    reset_application_state()
                    st.session_state.confirm_start_over = False
                    show_message("✅ Starting fresh! Create your new application.", "success")
                    st.rerun()
                else:
                    show_message(f"❌ Failed to clear: {result['error']}", "error")
            else:
                st.session_state.confirm_start_over = True
                show_message("⚠️ Click 'Start Over' again to confirm. This will delete your current application.", "warning")

    # Handle delete application
    if delete_app:
        if st.session_state.get('confirm_delete', False):
            result = api_client.cancel_application(application_id)
            if 'error' in result:
                show_message(f"❌ Failed to delete: {result['error']}", "error")
            else:
                reset_application_state()
                st.session_state.confirm_delete = False
                show_message("✅ Application deleted successfully!", "success")
                st.rerun()
        else:
            st.session_state.confirm_delete = True
            show_message("⚠️ Click 'Delete' again to confirm. This cannot be undone.", "warning")


def handle_new_application(full_name: str, emirates_id: str, phone: str, email: str, is_submit: bool):
    """Handle new application creation"""
    # For drafts, allow partial data
    if is_submit:
        # Validate form for submission
        if not validate_form_data(full_name, emirates_id, phone, email, is_submit):
            return
    else:
        # For draft, just check if at least one field is filled
        if not any([full_name.strip(), emirates_id.strip(), phone.strip(), email.strip()]):
            show_message("❌ Please fill in at least one field to save a draft.", "error")
            return

    # Save to session state
    update_form_data('full_name', full_name.strip())
    update_form_data('emirates_id', emirates_id.strip())
    update_form_data('phone', phone.strip())
    update_form_data('email', email.strip())

    if not is_submit:
        # Just save draft
        show_message("✅ Draft saved successfully! Your data will persist across sessions.", "success")
        return

    # Submit application
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
                # Handle existing application
                details = result.get('details', {})
                existing_app_id = details.get('existing_application_id')
                if existing_app_id and load_existing_application(existing_app_id, api_client):
                    show_message("📋 Found your existing application! Continuing where you left off.", "success")
                    st.rerun()
                else:
                    show_message("❌ You already have an active application. Please complete it first.", "error")
            else:
                show_message(f"❌ Submission failed: {result['error']}", "error")
        else:
            # Success - clear the new form widget states
            form_keys = ['full_name_new_form', 'emirates_id_new_form',
                        'phone_new_form', 'email_new_form']
            for key in form_keys:
                if key in st.session_state:
                    del st.session_state[key]

            application_id = result.get('application_id')
            if application_id and load_existing_application(application_id, api_client):
                show_message("🎉 Application submitted successfully! Upload your documents in the center panel.", "success")
                st.rerun()
            else:
                show_message("✅ Application submitted successfully!", "success")


def handle_form_update(application_id: str, full_name: str, emirates_id: str, phone: str, email: str, is_submit: bool):
    """Handle form update for existing application"""
    # Validate form
    if not validate_form_data(full_name, emirates_id, phone, email, True):
        return

    # Prepare all form data (send all fields to ensure consistency)
    update_data = {
        'full_name': full_name.strip(),
        'emirates_id': emirates_id.strip(),
        'phone': phone.strip(),
        'email': email.strip()
    }

    # Check if there's actually any data to update
    if not any(update_data.values()):
        show_message("❌ Please fill in at least one field.", "error")
        return
    
    # Check if form data has changed
    form_changed = False
    if 'original_form_data' in st.session_state:
        for field, value in update_data.items():
            if value != st.session_state.original_form_data.get(field, ''):
                form_changed = True
                break
    
    # If form changed and status is beyond form_submitted, reset to form_submitted
    if form_changed:
        current_state = st.session_state.get('processing_status', {}).get('current_state', 'draft')
        if current_state not in ['draft', 'form_submitted']:
            # Reset status to form_submitted since form data changed
            st.session_state.processing_status = {
                'current_state': 'form_submitted',
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'message': 'Form data updated - please re-submit documents'
            }
            # Reset document status as well
            if 'document_state' in st.session_state:
                for doc_type in st.session_state.document_state:
                    if st.session_state.document_state[doc_type].get('status') in ['submitted', 'processing', 'processed']:
                        st.session_state.document_state[doc_type]['status'] = 'uploaded'

    with st.spinner("💾 Updating application..."):
        result = api_client.update_application_form(application_id, update_data)

        if 'error' in result:
            show_message(f"❌ Update failed: {result['error']}", "error")
        else:
            # Clear form widget state to force refresh
            form_key = "edit_form"  # Match the key used in show_editable_form
            form_keys = [f'full_name_{form_key}', f'emirates_id_{form_key}',
                        f'phone_{form_key}', f'email_{form_key}']
            for key in form_keys:
                if key in st.session_state:
                    del st.session_state[key]

            # Update session state with new data immediately (complete replacement)
            st.session_state.application_form_data = {}
            for field, value in update_data.items():
                update_form_data(field, value)

            # Refresh application data from backend to ensure sync
            if load_existing_application(application_id, api_client):
                updated_fields = result.get('updated_fields', list(update_data.keys()))
                show_message(f"✅ Application updated successfully! Updated: {', '.join(updated_fields)}", "success")
            else:
                show_message("✅ Application updated successfully!", "success")

            # Force complete page refresh
            st.rerun()


def validate_form_data(full_name: str, emirates_id: str, phone: str, email: str, is_submit: bool) -> bool:
    """Validate form data with user-friendly error messages"""
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

    # Validate format if provided
    if full_name.strip():
        if len(full_name.strip()) < 2:
            errors.append("Full name must be at least 2 characters")
        if not re.match(r'^[a-zA-Z\s]+$', full_name.strip()):
            errors.append("Full name can only contain letters and spaces")

    if emirates_id.strip():
        if not re.match(r'^784-[0-9]{4}-[0-9]{7}-[0-9]$', emirates_id.strip()):
            errors.append("Invalid Emirates ID format. Use: 784-YYYY-XXXXXXX-X")

    if phone.strip():
        if not re.match(r'^(\+971|05)[0-9]{8,9}$', phone.strip()):
            errors.append("Invalid phone format. Use: +971XXXXXXXXX or 05XXXXXXXX")

    if email.strip():
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email.strip()):
            errors.append("Invalid email format")

    if errors:
        show_message("❌ " + " | ".join(errors), "error")
        return False

    return True


def show_message(content: str, message_type: str):
    """Show a message that persists properly"""
    st.session_state.app_message = {
        "content": content,
        "type": message_type
    }


# Helper function to clear any confirm states
def clear_confirm_states():
    """Clear confirmation states"""
    for key in ['confirm_reset', 'confirm_start_over', 'confirm_delete', 'confirm_new', 'confirm_cancel']:
        if key in st.session_state:
            del st.session_state[key]