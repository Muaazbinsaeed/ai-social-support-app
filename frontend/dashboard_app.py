"""
Main Streamlit dashboard application
"""

import streamlit as st
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from frontend.utils.dashboard_state import (
    initialize_session_state, is_authenticated, get_error_message,
    get_success_message, clear_messages
)
from frontend.utils.api_client import api_client
from frontend.utils.auth_cookies import initialize_auth_from_cookies, save_session_to_cookies
from frontend.components.auth_component import show_authentication, show_user_header
from frontend.components.navigation import show_navigation
from frontend.components.application_panel import show_application_panel
from frontend.components.document_management import show_enhanced_document_panel
from frontend.components.processing_status import show_processing_status
from frontend.components.status_panel import show_status_panel
from frontend.components.results_panel import show_results_panel
from frontend.components.ocr_display import show_enhanced_ocr_display


def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="Social Security AI",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }

    .status-panel {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #007bff;
    }

    .success-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem;
        border-radius: 0.375rem;
        margin-bottom: 1rem;
    }

    .error-message {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 0.375rem;
        margin-bottom: 1rem;
    }

    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }

    .stProgress > div > div > div > div {
        background-color: #28a745;
    }

    .step-completed {
        color: #28a745;
    }

    .step-in-progress {
        color: #ffc107;
    }

    .step-pending {
        color: #6c757d;
    }
    </style>
    """, unsafe_allow_html=True)


def show_main_header():
    """Show main application header"""
    st.markdown("""
    <div class="main-header">
        <h1>🏛️ Social Security AI Workflow Automation System</h1>
        <p>AI-powered government social security application processing - Complete your application in under 2 minutes</p>
    </div>
    """, unsafe_allow_html=True)


def show_system_status():
    """Show system status in sidebar"""
    with st.sidebar:
        st.header("🔧 System Status")

        # Get health status
        health_status = api_client.get_health_status()

        if 'error' in health_status:
            st.error("❌ System Offline")
            st.caption(f"Error: {health_status['error']}")
        else:
            overall_status = health_status.get('status', 'unknown')

            if overall_status == 'healthy':
                st.success("✅ All Systems Operational")
            elif overall_status == 'degraded':
                st.warning("⚠️ Limited Functionality")
            else:
                st.error("❌ System Issues")

            # Show service details
            services = health_status.get('services', {})
            if services:
                with st.expander("Service Details"):
                    for service_name, service_info in services.items():
                        status = service_info.get('status', 'unknown')
                        if status == 'healthy':
                            st.markdown(f"✅ {service_name.title()}")
                        elif status == 'degraded':
                            st.markdown(f"⚠️ {service_name.title()}")
                        elif status == 'warning':
                            st.markdown(f"⚠️ {service_name.title()}")
                        elif status == 'unavailable':
                            st.markdown(f"⭕ {service_name.title()} (Optional)")
                        elif status == 'unhealthy':
                            st.markdown(f"❌ {service_name.title()}")
                        else:
                            st.markdown(f"❓ {service_name.title()}")

        # Show API connection info
        st.markdown("---")
        st.markdown("**🔗 API Connection:**")
        api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        st.caption(f"Connected to: {api_url}")

        # Show current session info
        if is_authenticated():
            user_info = st.session_state.get('user_info', {})
            st.markdown("---")
            st.markdown("**👤 Current Session:**")
            st.caption(f"User: {user_info.get('username', 'N/A')}")
            if st.session_state.get('current_application_id'):
                st.caption(f"App ID: {st.session_state.current_application_id[:8]}...")


def show_messages():
    """Show error and success messages"""
    # Show error message
    error_msg = get_error_message()
    if error_msg:
        st.markdown(f"""
        <div class="error-message">
            {error_msg}
        </div>
        """, unsafe_allow_html=True)

    # Show success message
    success_msg = get_success_message()
    if success_msg:
        st.markdown(f"""
        <div class="success-message">
            {success_msg}
        </div>
        """, unsafe_allow_html=True)


def show_dashboard():
    """Show main dashboard interface"""
    # Show user header
    show_user_header()

    st.markdown("---")

    # Show navigation with My Applications
    show_navigation()

    st.markdown("---")

    # Check if we have results to show
    application_results = st.session_state.get('application_results')

    if application_results:
        # Show results panel at the top
        st.subheader("🎯 Application Results")
        show_results_panel()
        st.markdown("---")

    # Three-panel layout
    col1, col2, col3 = st.columns([1, 1, 1], gap="medium")

    with col1:
        # Left Panel: Application Form
        with st.container():
            show_application_panel()

    with col2:
        # Center Panel: Enhanced Document Management
        with st.container():
            show_enhanced_document_panel()

    with col3:
        # Right Panel: Processing Status with OCR Results
        with st.container():
            # Add tabs for different views
            tab1, tab2, tab3 = st.tabs(["📊 Processing Status", "🔍 Enhanced OCR", "📈 Summary"])

            with tab1:
                show_processing_status()

            with tab2:
                show_enhanced_ocr_display()

            with tab3:
                show_status_panel()

    # Show footer
    show_footer()


def show_footer():
    """Show application footer"""
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        st.markdown("**🏛️ Government of UAE**")
        st.caption("Ministry of Community Development")

    with col2:
        st.markdown("**📞 Support & Information**")
        st.caption("Phone: +971-4-123-4567 | Email: support@socialsecurity.gov.ae")
        st.caption("Hours: Sunday - Thursday, 8:00 AM - 4:00 PM")

    with col3:
        st.markdown("**🔒 Secure & Confidential**")
        st.caption("Your data is protected with government-grade security")

    # Technical footer
    st.markdown("---")
    st.caption("🤖 Powered by Social Security AI v1.0 | Built with ❤️ for digital government transformation")


def main():
    """Main application entry point"""
    # Configure page
    configure_page()

    # Initialize session state
    initialize_session_state()

    # Try to restore authentication from cookies
    if not is_authenticated():
        initialize_auth_from_cookies()

    # Show main header
    show_main_header()

    # Show system status in sidebar
    show_system_status()

    # Show messages
    show_messages()

    # Main application logic
    if not is_authenticated():
        # Show authentication
        show_authentication()
    else:
        # Show main dashboard
        show_dashboard()
        
        # Save session state to cookies for persistence
        save_session_to_cookies()

    # Clear messages at the end of each run
    clear_messages()


if __name__ == "__main__":
    main()