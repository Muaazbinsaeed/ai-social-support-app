"""
Processing status panel component
"""

import streamlit as st
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from frontend.utils.api_client import api_client
from frontend.utils.dashboard_state import (
    update_processing_status, update_application_results,
    set_error_message, should_refresh_status
)


def show_status_panel():
    """Show the processing status panel (right panel)"""
    st.subheader("📊 Processing Status")

    current_app_id = st.session_state.get('current_application_id')

    if not current_app_id:
        show_status_placeholder()
    else:
        show_application_status()


def show_status_placeholder():
    """Show placeholder when no application exists"""
    st.info("📋 **Submit your application to see status**")

    st.markdown("**Processing Steps:**")

    # Show all steps as pending
    steps = [
        ("📝", "Form Submitted", "⏳", "Waiting for application submission"),
        ("📤", "Documents Uploaded", "⏳", "Waiting for document upload"),
        ("🔍", "Scanning Documents", "⏳", "OCR text extraction"),
        ("💰", "Analyzing Income", "⏳", "Bank statement analysis"),
        ("🆔", "Analyzing Identity", "⏳", "Emirates ID verification"),
        ("⚖️", "Making Decision", "⏳", "AI eligibility evaluation"),
        ("🎉", "Decision Complete", "⏳", "Final results ready")
    ]

    for icon, step_name, status_icon, description in steps:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            st.markdown(f"{icon}")
        with col2:
            st.markdown(f"**{step_name}**")
            st.caption(description)
        with col3:
            st.markdown(f"{status_icon}")

    st.markdown("---")
    st.markdown("**⏱️ Estimated Total Time: 2 minutes**")


def show_application_status():
    """Show status for active application"""
    current_app_id = st.session_state.current_application_id

    # Auto-refresh logic
    if should_refresh_status():
        refresh_status_data(current_app_id)

    # Manual refresh button
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("🔄 Refresh Status", use_container_width=True, key="refresh_status_panel"):
            refresh_status_data(current_app_id)

    with col2:
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh", value=True)

    with col3:
        # Settings expander
        with st.expander("⚙️"):
            refresh_interval = st.slider("Refresh interval (seconds)", 3, 15, 5)

    st.markdown("---")

    # Get current status
    processing_status = st.session_state.get('processing_status')
    application_results = st.session_state.get('application_results')

    if processing_status:
        show_progress_tracking(processing_status)
        show_step_details(processing_status)

        # Check if processing is complete
        if processing_status.get('current_state') in ['approved', 'rejected', 'needs_review']:
            if not application_results:
                # Fetch results
                refresh_results_data(current_app_id)
    else:
        # Try to fetch initial status
        refresh_status_data(current_app_id)

    # Auto-refresh mechanism
    if auto_refresh and processing_status:
        current_state = processing_status.get('current_state', '')
        if current_state in ['processing', 'analyzing_income', 'analyzing_identity', 'making_decision']:
            time.sleep(refresh_interval)
            st.rerun()


def show_progress_tracking(status: Dict[str, Any]):
    """Show progress bar and overall status"""
    progress = status.get('progress', 0)
    current_state = status.get('current_state', '')

    # Progress bar
    progress_bar = st.progress(progress / 100)
    st.markdown(f"**Progress: {progress}% Complete**")

    # Current status
    state_messages = {
        'form_submitted': '📝 Application form received',
        'documents_uploaded': '📤 Documents uploaded successfully',
        'scanning_documents': '🔍 Scanning documents...',
        'ocr_completed': '✅ Text extraction completed',
        'analyzing_income': '💰 Analyzing bank statement...',
        'analyzing_identity': '🆔 Verifying Emirates ID...',
        'analysis_completed': '✅ Document analysis completed',
        'making_decision': '⚖️ Evaluating eligibility...',
        'decision_completed': '✅ Decision processing completed',
        'approved': '🎉 Application APPROVED',
        'rejected': '❌ Application REJECTED',
        'needs_review': '👀 Manual review required'
    }

    current_message = state_messages.get(current_state, f'Status: {current_state}')
    st.markdown(f"**{current_message}**")

    # Estimated completion time
    estimated_time = status.get('estimated_completion_time')
    if estimated_time and progress < 100:
        st.markdown(f"⏱️ **Estimated completion: {estimated_time} seconds**")

    st.markdown("---")


def show_step_details(status: Dict[str, Any]):
    """Show detailed step-by-step progress"""
    st.markdown("**📋 Processing Steps:**")

    steps = status.get('steps', [])
    current_state = status.get('current_state', '')

    # Define step order and details
    step_definitions = [
        {
            'name': 'form_submitted',
            'icon': '📝',
            'title': 'Form Submitted',
            'description': 'Application form received and validated'
        },
        {
            'name': 'documents_uploaded',
            'icon': '📤',
            'title': 'Documents Uploaded',
            'description': 'Documents received, starting analysis'
        },
        {
            'name': 'scanning_documents',
            'icon': '🔍',
            'title': 'Scanning Documents',
            'description': 'OCR text extraction in progress'
        },
        {
            'name': 'ocr_completed',
            'icon': '✅',
            'title': 'Text Extraction Complete',
            'description': 'Document text successfully extracted'
        },
        {
            'name': 'analyzing_income',
            'icon': '💰',
            'title': 'Analyzing Income',
            'description': 'Bank statement analysis in progress'
        },
        {
            'name': 'analyzing_identity',
            'icon': '🆔',
            'title': 'Verifying Identity',
            'description': 'Emirates ID verification in progress'
        },
        {
            'name': 'making_decision',
            'icon': '⚖️',
            'title': 'Making Decision',
            'description': 'AI eligibility evaluation in progress'
        },
        {
            'name': 'decision_completed',
            'icon': '🎉',
            'title': 'Decision Complete',
            'description': 'Processing completed successfully'
        }
    ]

    # Show each step
    for step_def in step_definitions:
        show_step_status(step_def, steps, current_state)

    # Show partial results if available
    show_partial_results(status)


def show_step_status(step_def: Dict[str, Any], steps: List[Dict[str, Any]], current_state: str):
    """Show individual step status"""
    step_name = step_def['name']

    # Find step data
    step_data = None
    for step in steps:
        if step.get('name') == step_name:
            step_data = step
            break

    # Determine status
    if step_data:
        step_status = step_data.get('status', 'pending')
        step_message = step_data.get('message', step_def['description'])
        duration = step_data.get('duration')
        completed_at = step_data.get('completed_at')
    else:
        if step_name == current_state:
            step_status = 'in_progress'
        elif current_state in ['approved', 'rejected', 'needs_review'] or \
             (step_name in ['form_submitted', 'documents_uploaded'] and current_state != 'draft'):
            step_status = 'completed'
        else:
            step_status = 'pending'
        step_message = step_def['description']
        duration = None
        completed_at = None

    # Status icons
    status_icons = {
        'completed': '✅',
        'in_progress': '◐',
        'pending': '⏳',
        'failed': '❌'
    }

    # Display step
    col1, col2, col3, col4 = st.columns([1, 3, 1, 1])

    with col1:
        st.markdown(f"{step_def['icon']}")

    with col2:
        st.markdown(f"**{step_def['title']}**")
        if step_status == 'in_progress':
            st.markdown(f"*{step_message}*")
        else:
            st.caption(step_message)

    with col3:
        st.markdown(f"{status_icons.get(step_status, '⏳')}")

    with col4:
        if duration:
            st.caption(f"{duration}")
        elif completed_at:
            st.caption("Done")


def show_partial_results(status: Dict[str, Any]):
    """Show partial processing results"""
    partial_results = status.get('partial_results', {})
    if not partial_results:
        return

    st.markdown("---")
    st.markdown("**📊 Extracted Information:**")

    # Bank statement results
    bank_data = partial_results.get('bank_statement', {})
    if bank_data:
        with st.expander("🏦 Bank Statement Analysis", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                monthly_income = bank_data.get('monthly_income')
                if monthly_income:
                    st.metric("Monthly Income", f"AED {monthly_income:,.2f}")

                confidence = bank_data.get('confidence')
                if confidence:
                    st.metric("Confidence", f"{float(confidence):.1%}")

            with col2:
                account_balance = bank_data.get('account_balance')
                if account_balance:
                    st.metric("Account Balance", f"AED {account_balance:,.2f}")

                processing_time = bank_data.get('processing_time')
                if processing_time:
                    st.metric("Processing Time", f"{processing_time}")

    # Emirates ID results
    emirates_data = partial_results.get('emirates_id', {})
    if emirates_data:
        with st.expander("🆔 Emirates ID Verification"):
            col1, col2 = st.columns(2)

            with col1:
                full_name = emirates_data.get('full_name')
                if full_name:
                    st.markdown(f"**Name:** {full_name}")

                id_number = emirates_data.get('id_number')
                if id_number:
                    st.markdown(f"**ID Number:** {id_number}")

            with col2:
                confidence = emirates_data.get('confidence')
                if confidence:
                    st.metric("Confidence", f"{float(confidence):.1%}")

                nationality = emirates_data.get('nationality')
                if nationality:
                    st.markdown(f"**Nationality:** {nationality}")


def refresh_status_data(application_id: str):
    """Refresh status data from API"""
    with st.spinner("Refreshing status..."):
        result = api_client.get_application_status(application_id)

        if 'error' in result:
            set_error_message(f"Failed to refresh status: {result['error']}")
        else:
            update_processing_status(result)
            st.rerun()


def refresh_results_data(application_id: str):
    """Refresh results data from API"""
    with st.spinner("Fetching results..."):
        result = api_client.get_application_results(application_id)

        if 'error' in result:
            if result.get('status_code') != 202:  # Not still processing
                set_error_message(f"Failed to fetch results: {result['error']}")
        else:
            update_application_results(result)
            st.rerun()


def show_error_recovery():
    """Show error recovery options"""
    st.markdown("---")
    st.error("⚠️ **Processing Error Detected**")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Retry Processing", use_container_width=True, key="retry_processing_btn"):
            retry_processing()

    with col2:
        if st.button("📞 Contact Support", use_container_width=True, key="contact_support_btn"):
            show_contact_support()


def retry_processing():
    """Retry failed processing"""
    current_app_id = st.session_state.get('current_application_id')
    if current_app_id:
        with st.spinner("Retrying processing..."):
            result = api_client.start_processing(current_app_id)
            if 'error' in result:
                set_error_message(f"Retry failed: {result['error']}")
            else:
                update_processing_status(result)
                st.success("✅ Processing restarted successfully!")
                st.rerun()


def show_contact_support():
    """Show contact support information"""
    st.info("""
    **📞 Support Contact Information:**

    - **Phone:** +971-4-123-4567
    - **Email:** support@socialsecurity.gov.ae
    - **Hours:** Sunday - Thursday, 8:00 AM - 4:00 PM

    **Application ID:** `{}`
    """.format(st.session_state.get('current_application_id', 'N/A')))