"""
Navigation component with My Applications section
"""

import streamlit as st
from frontend.utils.api_client import api_client
from frontend.utils.dashboard_state import (
    set_current_application, load_existing_application, reset_application_state
)


def show_navigation():
    """Show navigation bar with single application management"""
    st.markdown("### 🧭 Your Application")
    
    # Single application view - no tabs
    show_single_application_status()


def show_single_application_status():
    """Show single application status - one application per user"""
    current_app_id = st.session_state.get('current_application_id')
    processing_status = st.session_state.get('processing_status', {})
    
    if current_app_id:
        # User has an application
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.success(f"**Application ID:** {current_app_id[:8]}...")
            
        with col2:
            status = processing_status.get('current_state', 'draft')
            st.info(f"**Status:** {status.replace('_', ' ').title()}")
            
        with col3:
            progress = processing_status.get('progress', 0)
            if progress > 0:
                st.metric("Progress", f"{progress}%")
        
        # Show decision if available
        if processing_status.get('decision'):
            decision = processing_status['decision']
            if decision == 'approved':
                st.success("✅ **Application Approved!**")
                if processing_status.get('benefit_amount'):
                    st.success(f"💰 Monthly Benefit: AED {processing_status['benefit_amount']}")
            elif decision == 'rejected':
                st.error("❌ **Application Rejected**")
            elif decision == 'needs_review':
                st.warning("⏳ **Application Under Review**")
    else:
        # No application yet
        st.info("📝 **No Application Yet** - Start by filling out the form below")
        
        # Auto-search for existing application on first load
        if st.session_state.get('first_load', True):
            with st.spinner("🔍 Checking for existing application..."):
                found_app = search_user_application()
                if found_app:
                    st.success("✅ Found your existing application!")
                    st.rerun()
                else:
                    st.session_state.first_load = False


def search_user_application():
    """Search for user's single application"""
    try:
        # Get user's applications
        apps_result = api_client.get_user_applications()
        if 'error' not in apps_result:
            applications = apps_result.get('applications', [])
            # Get the most recent active application (should be only one)
            for app in applications:
                if app.get('status') not in ['cancelled', 'expired']:
                    app_id = app.get('application_id') or app.get('id')
                    if app_id and load_existing_application(app_id, api_client):
                        return app_id
        return None
    except Exception:
        return None


def show_current_application_section():
    """Show current application status and controls"""
    current_app_id = st.session_state.get('current_application_id')

    if current_app_id:
        st.success(f"**Active Application:** {current_app_id[:8]}...")
        processing_status = st.session_state.get('processing_status')
        if processing_status:
            status = processing_status.get('current_state', 'draft')
            progress = processing_status.get('progress', 0)
            st.info(f"Status: {status.replace('_', ' ').title()} | Progress: {progress}%")

        # New Application button
        if st.button("🆕 Start New Application", type="primary", use_container_width=True, key="nav_start_new_app"):
            # Discard current application and reset state
            discard_result = api_client.discard_current_application()
            if 'error' in discard_result:
                st.error(f"Failed to discard current application: {discard_result['error']}")
            else:
                reset_application_state()
                st.success("Current application discarded. Ready to start a new application!")
                st.rerun()
    else:
        st.info("No active application")
        if st.button("🆕 Create New Application", type="primary", use_container_width=True, key="nav_create_new_app"):
            reset_application_state()
            st.success("Ready to create your application!")
            st.rerun()


def show_my_applications_section():
    """Show application history and management"""
    with st.spinner("Loading your applications..."):
        history_result = api_client.get_application_history()

    if 'error' in history_result:
        st.error(f"Failed to load applications: {history_result['error']}")
        return

    active_app = history_result.get('active_application')
    historical_apps = history_result.get('historical_applications', [])
    total_count = history_result.get('total_count', 0)

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Applications", total_count)
    with col2:
        st.metric("Active", 1 if active_app else 0)
    with col3:
        st.metric("Historical", len(historical_apps))

    st.markdown("---")

    # Active application section
    if active_app:
        st.subheader("🔄 Active Application")
        show_application_card(active_app, is_active=True)
        st.markdown("---")

    # Historical applications section
    if historical_apps:
        st.subheader("📜 Application History")
        for app in historical_apps:
            show_application_card(app, is_active=False)

    if not active_app and not historical_apps:
        st.info("You haven't created any applications yet. Start by creating your first application!")


def show_application_card(app, is_active=False):
    """Show individual application card"""
    app_id = app['application_id']
    status = app['status']
    progress = app.get('progress', 0)
    created_at = app.get('created_at', '')
    decision = app.get('decision')
    benefit_amount = app.get('benefit_amount')

    # Format creation date
    try:
        from datetime import datetime
        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        formatted_date = created_date.strftime("%B %d, %Y at %I:%M %p")
    except:
        formatted_date = created_at

    # Create expandable card
    with st.expander(f"📋 Application {app_id[:8]}... | {status.replace('_', ' ').title()}", expanded=is_active):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**Status:** {status.replace('_', ' ').title()}")
            st.markdown(f"**Created:** {formatted_date}")

            if progress > 0:
                st.progress(progress / 100.0)
                st.caption(f"Progress: {progress}%")

            if decision:
                if decision == 'approved':
                    st.success(f"✅ **Approved**")
                    if benefit_amount:
                        st.success(f"💰 Benefit: AED {benefit_amount}/month")
                elif decision == 'rejected':
                    st.error("❌ **Rejected**")
                elif decision == 'needs_review':
                    st.warning("⏳ **Under Review**")

            # Show form data if available
            form_data = app.get('form_data')
            if form_data and form_data.get('full_name'):
                st.markdown("**Applicant:** " + form_data.get('full_name', 'N/A'))

        with col2:
            # Action buttons
            if is_active:
                if st.button("📖 Load Application", key=f"load_{app_id}", use_container_width=True):
                    if load_existing_application(app_id, api_client):
                        st.success("Application loaded successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to load application")
            else:
                if st.button("👁️ View Details", key=f"view_{app_id}", use_container_width=True):
                    # Load historical application for viewing
                    if load_existing_application(app_id, api_client):
                        st.success("Historical application loaded for viewing")
                        st.rerun()
                    else:
                        st.error("Failed to load application details")

            # Copy application ID
            if st.button("📋 Copy ID", key=f"copy_{app_id}", use_container_width=True):
                st.code(app_id, language=None)
                st.success("Application ID displayed above!")


def get_status_color(status):
    """Get color for status badge"""
    status_colors = {
        'draft': '🟡',
        'form_submitted': '🟡',
        'documents_uploaded': '🟡',
        'scanning_documents': '🟠',
        'ocr_completed': '🟠',
        'analyzing_income': '🟠',
        'analyzing_identity': '🟠',
        'analysis_completed': '🟠',
        'making_decision': '🟠',
        'decision_completed': '🔵',
        'approved': '🟢',
        'rejected': '🔴',
        'needs_review': '🟡'
    }
    return status_colors.get(status, '⚪')