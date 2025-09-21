"""
Workflow Steps Manager Component
Provides manual control over document processing workflow steps
"""

import streamlit as st
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from frontend.utils.api_client import api_client
from frontend.utils.dashboard_state import get_current_application_id


# Step descriptions for UI
STEP_DESCRIPTIONS = {
    "ocr_extraction": {
        "title": "📝 OCR Text Extraction",
        "description": "Extract text from uploaded documents using OCR technology",
        "icon": "📝",
        "expected_time": 60
    },
    "document_validation": {
        "title": "✅ Document Validation",
        "description": "Validate document format and content requirements",
        "icon": "✅",
        "expected_time": 30
    },
    "income_analysis": {
        "title": "💰 Income Analysis",
        "description": "Analyze income from bank statements",
        "icon": "💰",
        "expected_time": 45
    },
    "identity_verification": {
        "title": "🆔 Identity Verification",
        "description": "Verify identity from Emirates ID",
        "icon": "🆔",
        "expected_time": 45
    },
    "ai_analysis": {
        "title": "🤖 AI Document Analysis",
        "description": "Comprehensive AI-based document analysis",
        "icon": "🤖",
        "expected_time": 90
    },
    "decision_making": {
        "title": "⚖️ Decision Making",
        "description": "Make final eligibility decision",
        "icon": "⚖️",
        "expected_time": 60
    }
}


def show_workflow_steps_manager():
    """Main component for workflow steps management"""
    
    st.markdown("## 🔄 Workflow Steps Manager")
    st.markdown("Control and monitor each step of the document processing workflow")
    
    # Get current application
    app_id = get_current_application_id()
    if not app_id:
        st.warning("⚠️ No application selected. Please create or load an application first.")
        return
    
    # Add control buttons
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.info(f"📋 Application ID: `{app_id}`")
    
    with col2:
        if st.button("🔄 Refresh Status", key="refresh_workflow_steps"):
            st.rerun()
    
    with col3:
        auto_refresh = st.checkbox("Auto-refresh", value=False, key="auto_refresh_workflow")
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(3)
        st.rerun()
    
    # Get workflow steps status
    with st.spinner("Loading workflow status..."):
        status_response = api_client._make_request('GET', f'/workflow-steps/status/{app_id}')
    
    if 'error' in status_response:
        st.error(f"❌ Failed to load workflow status: {status_response['error']}")
        return
    
    # Display overall progress
    show_overall_progress(status_response)
    
    # Display workflow steps
    st.markdown("### 📊 Workflow Steps")
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["🎮 Manual Control", "📈 Status Overview", "📝 Execution Logs"])
    
    with tab1:
        show_manual_controls(app_id, status_response)
    
    with tab2:
        show_status_overview(status_response)
    
    with tab3:
        show_execution_logs(status_response)


def show_overall_progress(status_data: Dict[str, Any]):
    """Display overall workflow progress"""
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current State", status_data.get('current_state', 'unknown').replace('_', ' ').title())
    
    with col2:
        progress = status_data.get('overall_progress', 0)
        st.metric("Overall Progress", f"{progress}%")
    
    with col3:
        completed = sum(1 for s in status_data.get('steps', []) if s['status'] == 'completed')
        total = len(status_data.get('steps', []))
        st.metric("Steps Completed", f"{completed}/{total}")
    
    # Progress bar
    st.progress(status_data.get('overall_progress', 0) / 100)


def show_manual_controls(app_id: str, status_data: Dict[str, Any]):
    """Show manual control buttons for each step"""
    
    st.markdown("#### 🎮 Manual Step Execution")
    st.markdown("Execute workflow steps manually with full control over the process.")
    
    # Create a grid of step controls
    for step in status_data.get('steps', []):
        step_name = step['name']
        step_info = STEP_DESCRIPTIONS.get(step_name, {})
        
        with st.expander(f"{step_info.get('icon', '📄')} {step['display_name']}", expanded=(step['status'] == 'running')):
            # Step description
            st.markdown(f"**Description:** {step['description']}")
            st.markdown(f"**Expected Time:** {step_info.get('expected_time', 60)} seconds")
            
            # Status display
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                status_color = get_status_color(step['status'])
                st.markdown(f"**Status:** <span style='color: {status_color}'>{step['status'].replace('_', ' ').title()}</span>", unsafe_allow_html=True)
                
                if step.get('progress', 0) > 0 and step['status'] == 'running':
                    st.progress(step['progress'] / 100)
            
            with col2:
                if step.get('started_at'):
                    started = datetime.fromisoformat(step['started_at'].replace('Z', '+00:00'))
                    st.caption(f"Started: {started.strftime('%H:%M:%S')}")
            
            with col3:
                if step.get('duration_seconds'):
                    st.caption(f"Duration: {step['duration_seconds']:.1f}s")
            
            # Control buttons
            button_col1, button_col2, button_col3 = st.columns(3)
            
            with button_col1:
                # Execute button
                if step['status'] not in ['running', 'completed']:
                    if step['can_execute']:
                        if st.button(f"▶️ Execute", key=f"exec_{step_name}", use_container_width=True):
                            execute_step(app_id, step_name)
                    else:
                        st.button(f"🔒 Prerequisites Not Met", key=f"locked_{step_name}", disabled=True, use_container_width=True)
                elif step['status'] == 'running':
                    if st.button(f"⏹️ Cancel", key=f"cancel_{step_name}", use_container_width=True):
                        cancel_step(app_id, step_name)
                else:
                    if st.button(f"🔄 Re-execute", key=f"reexec_{step_name}", use_container_width=True):
                        execute_step(app_id, step_name, force=True)
            
            with button_col2:
                # Force execute button
                if step['status'] not in ['running', 'completed'] and not step['can_execute']:
                    if st.button(f"⚡ Force Execute", key=f"force_{step_name}", use_container_width=True, help="Execute even if prerequisites are not met"):
                        execute_step(app_id, step_name, force=True)
            
            with button_col3:
                # View output button
                if step.get('output'):
                    if st.button(f"👁️ View Output", key=f"view_{step_name}", use_container_width=True):
                        st.session_state[f"show_output_{step_name}"] = True
            
            # Show output if requested
            if st.session_state.get(f"show_output_{step_name}"):
                st.markdown("##### 📤 Step Output")
                st.json(step['output'])
                if st.button(f"Close Output", key=f"close_output_{step_name}"):
                    st.session_state[f"show_output_{step_name}"] = False
            
            # Show error if any
            if step.get('error'):
                st.error(f"❌ Error: {step['error']}")
            
            # Show prerequisites
            if not step['can_execute'] and step['status'] not in ['completed', 'running']:
                prereqs = STEP_DESCRIPTIONS.get(step_name, {}).get('prerequisites', [])
                if prereqs:
                    st.warning(f"⚠️ Prerequisites: {', '.join(prereqs)}")


def show_status_overview(status_data: Dict[str, Any]):
    """Show status overview of all steps"""
    
    st.markdown("#### 📈 Workflow Status Overview")
    
    # Create a visual pipeline
    steps = status_data.get('steps', [])
    
    # Timeline view
    for i, step in enumerate(steps):
        step_info = STEP_DESCRIPTIONS.get(step['name'], {})
        
        col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
        
        with col1:
            # Status icon
            if step['status'] == 'completed':
                st.success(step_info.get('icon', '📄'))
            elif step['status'] == 'running':
                st.info(step_info.get('icon', '📄'))
            elif step['status'] == 'failed':
                st.error(step_info.get('icon', '📄'))
            else:
                st.markdown(f"⏳ {step_info.get('icon', '📄')}")
        
        with col2:
            # Step name and status
            st.markdown(f"**{step['display_name']}**")
            status_color = get_status_color(step['status'])
            st.markdown(f"<span style='color: {status_color}'>{step['status'].replace('_', ' ').title()}</span>", unsafe_allow_html=True)
        
        with col3:
            # Timing information
            if step.get('started_at'):
                st.caption(f"Started: {step['started_at']}")
            if step.get('duration_seconds'):
                st.caption(f"Duration: {step['duration_seconds']:.1f}s")
        
        with col4:
            # Progress or output summary
            if step['status'] == 'running' and step.get('progress'):
                st.progress(step['progress'] / 100)
            elif step['status'] == 'completed' and step.get('output'):
                # Show summary of output
                if 'documents_processed' in step.get('output', {}):
                    st.success(f"✅ {step['output']['documents_processed']} docs processed")
                elif 'decision' in step.get('output', {}):
                    decision = step['output'].get('decision', {}).get('decision', 'unknown')
                    if decision == 'approved':
                        st.success("✅ Approved")
                    else:
                        st.error("❌ Rejected")
        
        # Add connector line (except for last step)
        if i < len(steps) - 1:
            if step['status'] == 'completed':
                st.markdown("⬇️")
            else:
                st.markdown("⬜")


def show_execution_logs(status_data: Dict[str, Any]):
    """Show detailed execution logs"""
    
    st.markdown("#### 📝 Execution Logs")
    
    # Filter options
    col1, col2 = st.columns(2)
    
    with col1:
        log_filter = st.selectbox(
            "Filter by status",
            ["All", "Completed", "Failed", "Running", "Not Started"],
            key="log_filter"
        )
    
    with col2:
        show_details = st.checkbox("Show detailed output", value=False, key="show_log_details")
    
    # Display logs
    steps = status_data.get('steps', [])
    
    # Filter steps based on selection
    if log_filter != "All":
        filter_status = log_filter.lower().replace(' ', '_')
        steps = [s for s in steps if s['status'] == filter_status]
    
    # Show logs
    for step in steps:
        step_info = STEP_DESCRIPTIONS.get(step['name'], {})
        
        # Create log entry
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                status_icon = "✅" if step['status'] == 'completed' else "❌" if step['status'] == 'failed' else "🔄" if step['status'] == 'running' else "⏳"
                st.markdown(f"{status_icon} **{step['display_name']}**")
                
                if step.get('started_at'):
                    st.caption(f"Started: {step['started_at']}")
                
                if step.get('error'):
                    st.error(f"Error: {step['error']}")
                
                if show_details and step.get('output'):
                    st.json(step['output'])
            
            with col2:
                st.markdown(f"**Status:** {step['status']}")
                if step.get('duration_seconds'):
                    st.caption(f"Duration: {step['duration_seconds']:.1f}s")
            
            st.markdown("---")


def execute_step(app_id: str, step_name: str, force: bool = False):
    """Execute a workflow step"""
    
    with st.spinner(f"Executing {step_name}..."):
        response = api_client._make_request(
            'POST',
            f'/workflow-steps/execute/{app_id}',
            json={
                "step_name": step_name,
                "timeout_seconds": 60,
                "force": force
            }
        )
    
    if 'error' in response:
        st.error(f"❌ Failed to execute step: {response['error']}")
    else:
        st.success(f"✅ Step execution started: {response.get('status', 'unknown')}")
        time.sleep(2)
        st.rerun()


def cancel_step(app_id: str, step_name: str):
    """Cancel a running workflow step"""
    
    with st.spinner(f"Cancelling {step_name}..."):
        response = api_client._make_request(
            'POST',
            f'/workflow-steps/cancel/{app_id}/{step_name}'
        )
    
    if 'error' in response:
        st.error(f"❌ Failed to cancel step: {response['error']}")
    else:
        st.warning(f"⏹️ Step cancelled")
        time.sleep(1)
        st.rerun()


def get_status_color(status: str) -> str:
    """Get color for status display"""
    status_colors = {
        'not_started': '#808080',
        'running': '#FF9800',
        'completed': '#4CAF50',
        'failed': '#F44336',
        'cancelled': '#9E9E9E',
        'timeout': '#FF5722'
    }
    return status_colors.get(status, '#808080')
