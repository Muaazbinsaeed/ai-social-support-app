"""
Dashboard state management for Streamlit
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime


def initialize_session_state():
    """Initialize session state variables"""
    # Authentication state
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'is_authenticated' not in st.session_state:
        st.session_state.is_authenticated = False

    # Application state
    if 'current_application_id' not in st.session_state:
        st.session_state.current_application_id = None
    if 'application_form_data' not in st.session_state:
        st.session_state.application_form_data = {}
    if 'uploaded_documents' not in st.session_state:
        st.session_state.uploaded_documents = {}
    if 'processing_status' not in st.session_state:
        st.session_state.processing_status = None
    if 'application_results' not in st.session_state:
        st.session_state.application_results = None

    # UI state
    if 'show_login' not in st.session_state:
        st.session_state.show_login = True
    if 'show_register' not in st.session_state:
        st.session_state.show_register = False
    if 'refresh_status' not in st.session_state:
        st.session_state.refresh_status = False
    if 'last_status_update' not in st.session_state:
        st.session_state.last_status_update = None

    # Error handling
    if 'last_error' not in st.session_state:
        st.session_state.last_error = None
    if 'success_message' not in st.session_state:
        st.session_state.success_message = None


def set_authentication(token: str, user_info: Dict[str, Any]):
    """Set authentication state"""
    st.session_state.access_token = token
    st.session_state.user_info = user_info
    st.session_state.is_authenticated = True
    st.session_state.show_login = False


def clear_authentication():
    """Clear authentication state"""
    st.session_state.access_token = None
    st.session_state.user_info = None
    st.session_state.is_authenticated = False
    st.session_state.show_login = True

    # Clear application data
    st.session_state.current_application_id = None
    st.session_state.application_form_data = {}
    st.session_state.uploaded_documents = {}
    st.session_state.processing_status = None
    st.session_state.application_results = None


def set_current_application(application_id: str):
    """Set current application"""
    st.session_state.current_application_id = application_id


def update_form_data(field: str, value: Any):
    """Update application form data"""
    if 'application_form_data' not in st.session_state:
        st.session_state.application_form_data = {}
    st.session_state.application_form_data[field] = value


def get_form_data(field: str, default: Any = None) -> Any:
    """Get application form data"""
    return st.session_state.application_form_data.get(field, default)


def add_uploaded_document(doc_type: str, file_name: str, file_content: bytes):
    """Add uploaded document to session state"""
    if 'uploaded_documents' not in st.session_state:
        st.session_state.uploaded_documents = {}
    st.session_state.uploaded_documents[doc_type] = {
        'file_name': file_name,
        'file_content': file_content,
        'uploaded_at': datetime.now()
    }


def get_uploaded_document(doc_type: str) -> Optional[Dict[str, Any]]:
    """Get uploaded document from session state"""
    return st.session_state.uploaded_documents.get(doc_type)


def clear_uploaded_documents():
    """Clear all uploaded documents"""
    st.session_state.uploaded_documents = {}


def update_processing_status(status: Dict[str, Any]):
    """Update processing status"""
    st.session_state.processing_status = status
    st.session_state.last_status_update = datetime.now()


def get_processing_status() -> Optional[Dict[str, Any]]:
    """Get current processing status"""
    return st.session_state.processing_status


def update_application_results(results: Dict[str, Any]):
    """Update application results"""
    st.session_state.application_results = results


def get_application_results() -> Optional[Dict[str, Any]]:
    """Get application results"""
    return st.session_state.application_results


def set_error_message(message: str):
    """Set error message"""
    st.session_state.last_error = message
    st.session_state.success_message = None


def set_success_message(message: str):
    """Set success message"""
    st.session_state.success_message = message
    st.session_state.last_error = None


def clear_messages():
    """Clear all messages"""
    st.session_state.last_error = None
    st.session_state.success_message = None


def get_error_message() -> Optional[str]:
    """Get and clear error message"""
    error = st.session_state.last_error
    st.session_state.last_error = None
    return error


def get_success_message() -> Optional[str]:
    """Get and clear success message"""
    success = st.session_state.success_message
    st.session_state.success_message = None
    return success


def reset_application_state():
    """Reset application state for new application"""
    st.session_state.current_application_id = None
    st.session_state.application_form_data = {}
    st.session_state.uploaded_documents = {}
    st.session_state.processing_status = None
    st.session_state.application_results = None
    st.session_state.last_status_update = None


def is_authenticated() -> bool:
    """Check if user is authenticated"""
    return (
        st.session_state.get('is_authenticated', False) and
        st.session_state.get('access_token') is not None
    )


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current user info"""
    return st.session_state.get('user_info')


def should_refresh_status() -> bool:
    """Check if status should be refreshed"""
    if not st.session_state.processing_status:
        return False

    last_update = st.session_state.last_status_update
    if not last_update:
        return True

    # Refresh every 5 seconds if processing
    status = st.session_state.processing_status.get('current_state', '')
    if status in ['processing', 'analyzing_income', 'analyzing_identity', 'making_decision']:
        time_diff = (datetime.now() - last_update).total_seconds()
        return time_diff >= 5

    return False


def toggle_refresh_status():
    """Toggle status refresh flag"""
    st.session_state.refresh_status = not st.session_state.refresh_status