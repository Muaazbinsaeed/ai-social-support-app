"""
Workflow Steps Control Component - Manual control for each processing step
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import time
from frontend.utils.api_client import api_client
from frontend.utils.dashboard_state import get_current_application_id


# Define workflow steps
WORKFLOW_STEPS = [
    {
        "type": "validate_documents",
        "name": "📋 Document Validation",
        "description": "Validate uploaded documents for format and completeness",
        "icon": "🔍",
        "timeout": 30
    },
    {
        "type": "ocr_extraction", 
        "name": "📝 OCR Text Extraction",
        "description": "Extract text from documents using OCR (Pytesseract)",
        "icon": "📄",
        "timeout": 60
    },
    {
        "type": "text_analysis",
        "name": "🔤 Text Analysis",
        "description": "Analyze extracted text for quality and content",
        "icon": "📊",
        "timeout": 45
    },
    {
        "type": "data_extraction",
        "name": "🎯 Data Extraction",
        "description": "Extract structured data (names, IDs, amounts)",
        "icon": "💎",
        "timeout": 30
    },
    {
        "type": "income_verification",
        "name": "💰 Income Verification",
        "description": "Verify income from bank statement",
        "icon": "💳",
        "timeout": 30
    },
    {
        "type": "identity_verification",
        "name": "🆔 Identity Verification",
        "description": "Verify identity from Emirates ID",
        "icon": "👤",
        "timeout": 30
    },
    {
        "type": "decision_making",
        "name": "⚖️ Decision Making",
        "description": "Make eligibility decision based on all data",
        "icon": "🤔",
        "timeout": 45
    },
    {
        "type": "final_review",
        "name": "✅ Final Review",
        "description": "Final review and approval",
        "icon": "📋",
        "timeout": 20
    }
]


def show_workflow_steps_control():
    """Display workflow steps with manual control"""
    current_app_id = get_current_application_id()
    
    if not current_app_id:
        st.info("📋 No application selected. Please submit an application first.")
        return
    
    st.markdown("### 🎛️ Manual Workflow Control")
    st.markdown("Control each processing step individually with detailed output and timing.")
    
    # Add refresh button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("#### Processing Steps")
    with col2:
        if st.button("🔄 Refresh All", use_container_width=True, key="refresh_all_steps"):
            st.rerun()
    
    # Get all steps status
    all_steps_result = api_client.get_workflow_steps_status(current_app_id)
    
    if 'error' in all_steps_result:
        st.error(f"❌ Failed to load steps status: {all_steps_result['error']}")
        return
    
    steps_status = {}
    if all_steps_result and 'steps' in all_steps_result:
        for step in all_steps_result['steps']:
            steps_status[step['step_type']] = step
    
    # Display each step
    for i, step_config in enumerate(WORKFLOW_STEPS):
        display_workflow_step(current_app_id, step_config, steps_status.get(step_config['type'], {}), i + 1)


def display_workflow_step(app_id: str, step_config: Dict, step_status: Dict, step_number: int):
    """Display individual workflow step with controls"""
    
    # Create expandable section for each step
    with st.expander(f"{step_config['icon']} Step {step_number}: {step_config['name']}", expanded=True):
        # Step description
        st.markdown(f"**Description:** {step_config['description']}")
        
        # Status information
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            status = step_status.get('status', 'pending')
            status_color = get_status_color(status)
            st.markdown(f"**Status:** <span style='color: {status_color}'>{status.upper()}</span>", unsafe_allow_html=True)
            
            if step_status.get('started_at'):
                started = datetime.fromisoformat(step_status['started_at'].replace('Z', '+00:00'))
                st.caption(f"Started: {started.strftime('%H:%M:%S')}")
        
        with col2:
            if step_status.get('duration_ms'):
                duration = step_status['duration_ms'] / 1000
                st.metric("Duration", f"{duration:.2f}s")
            elif status == 'running':
                # Show progress for running steps
                progress = st.progress(0)
                placeholder = st.empty()
                # Simulate progress (in real app, get from backend)
                for i in range(100):
                    time.sleep(0.01)
                    progress.progress(i + 1)
                    placeholder.text(f"Progress: {i+1}%")
        
        with col3:
            # Control buttons
            if status == 'pending' or status == 'failed' or status == 'cancelled':
                if st.button(f"▶️ Start", key=f"start_{step_config['type']}", use_container_width=True):
                    execute_step(app_id, step_config)
            elif status == 'running':
                if st.button(f"⏹️ Cancel", key=f"cancel_{step_config['type']}", use_container_width=True):
                    cancel_step(app_id, step_config['type'])
            elif status == 'completed':
                if st.button(f"🔄 Retry", key=f"retry_{step_config['type']}", use_container_width=True):
                    execute_step(app_id, step_config, retry=True)
        
        # Show error if any
        if step_status.get('error'):
            st.error(f"❌ Error: {step_status['error']}")
        
        # Show output if available
        if step_status.get('has_output'):
            show_step_output(app_id, step_config['type'])
        
        # Timeout configuration
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                timeout = st.slider(
                    "Timeout (seconds)",
                    min_value=10,
                    max_value=300,
                    value=step_config['timeout'],
                    key=f"timeout_{step_config['type']}"
                )
            with col2:
                st.caption(f"Default: {step_config['timeout']}s")


def execute_step(app_id: str, step_config: Dict, retry: bool = False):
    """Execute a workflow step"""
    with st.spinner(f"Starting {step_config['name']}..."):
        timeout = st.session_state.get(f"timeout_{step_config['type']}", step_config['timeout'])
        
        result = api_client.execute_workflow_step(
            app_id,
            step_config['type'],
            timeout,
            retry
        )
        
        if 'error' in result:
            st.error(f"❌ Failed to start step: {result['error']}")
        else:
            st.success(f"✅ {step_config['name']} started!")
            time.sleep(1)
            st.rerun()


def cancel_step(app_id: str, step_type: str):
    """Cancel a running step"""
    result = api_client.cancel_workflow_step(app_id, step_type)
    
    if 'error' in result:
        st.error(f"❌ Failed to cancel step: {result['error']}")
    else:
        st.warning(f"⏹️ Step cancelled")
        time.sleep(1)
        st.rerun()


def show_step_output(app_id: str, step_type: str):
    """Display step output"""
    result = api_client.get_workflow_step_status(app_id, step_type)
    
    if 'error' not in result and result.get('output'):
        st.markdown("#### 📊 Step Output")
        
        output = result['output']
        
        # Format output based on step type
        if step_type == 'validate_documents':
            show_validation_output(output)
        elif step_type == 'ocr_extraction':
            show_ocr_output(output)
        elif step_type == 'text_analysis':
            show_analysis_output(output)
        elif step_type == 'data_extraction':
            show_extraction_output(output)
        elif step_type == 'income_verification':
            show_income_output(output)
        elif step_type == 'identity_verification':
            show_identity_output(output)
        elif step_type == 'decision_making':
            show_decision_output(output)
        else:
            # Generic output display
            st.json(output)


def show_validation_output(output: Dict):
    """Display document validation output"""
    st.markdown("**Validation Results:**")
    
    if 'validation_results' in output:
        for validation in output['validation_results']:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"📄 **{validation['document_type']}**")
            with col2:
                st.markdown(f"File: {validation['filename']}")
            with col3:
                if validation['status'] == 'valid':
                    st.success("✅ Valid")
                else:
                    st.error("❌ Invalid")


def show_ocr_output(output: Dict):
    """Display OCR extraction output"""
    st.markdown("**OCR Results:**")
    
    if 'ocr_results' in output:
        for ocr_result in output['ocr_results']:
            if 'error' in ocr_result:
                st.error(f"❌ {ocr_result['document_type']}: {ocr_result['error']}")
            else:
                with st.container():
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"📄 **{ocr_result['document_type']}**")
                    with col2:
                        st.metric("Text Length", f"{ocr_result['text_length']} chars")
                    with col3:
                        st.metric("Confidence", f"{ocr_result['confidence']:.1%}")
                    
                    # Show text preview
                    if 'preview' in ocr_result:
                        st.text_area(
                            "Text Preview",
                            value=ocr_result['preview'],
                            height=100,
                            disabled=True,
                            key=f"ocr_preview_{ocr_result['document_type']}"
                        )
    
    if 'total_text_extracted' in output:
        st.info(f"📊 Total text extracted: {output['total_text_extracted']} characters")


def show_analysis_output(output: Dict):
    """Display text analysis output"""
    st.markdown("**Analysis Results:**")
    
    if 'analysis_results' in output:
        for analysis in output['analysis_results']:
            with st.container():
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"📄 **{analysis['document_type']}**")
                with col2:
                    st.metric("Words", analysis['word_count'])
                with col3:
                    st.metric("Lines", analysis['line_count'])
                with col4:
                    st.metric("Quality", f"{analysis['quality_score']:.1%}")


def show_extraction_output(output: Dict):
    """Display data extraction output"""
    st.markdown("**Extracted Data:**")
    
    if 'extracted_data' in output:
        for doc_type, data in output['extracted_data'].items():
            st.markdown(f"**{doc_type.replace('_', ' ').title()}:**")
            for key, value in data.items():
                st.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")


def show_income_output(output: Dict):
    """Display income verification output"""
    st.markdown("**Income Verification:**")
    
    col1, col2 = st.columns(2)
    with col1:
        if output.get('income_verified'):
            st.success("✅ Income Verified")
        else:
            st.error("❌ Income Not Verified")
        
        st.metric("Monthly Income", f"{output.get('monthly_income', 0)} {output.get('currency', 'AED')}")
    
    with col2:
        if output.get('meets_threshold'):
            st.success("✅ Meets Threshold")
        else:
            st.error("❌ Below Threshold")
        
        st.metric("Threshold", f"{output.get('threshold', 0)} {output.get('currency', 'AED')}")
    
    st.metric("Confidence", f"{output.get('confidence', 0):.1%}")


def show_identity_output(output: Dict):
    """Display identity verification output"""
    st.markdown("**Identity Verification:**")
    
    col1, col2 = st.columns(2)
    with col1:
        if output.get('identity_verified'):
            st.success("✅ Identity Verified")
        else:
            st.error("❌ Identity Not Verified")
    
    with col2:
        if output.get('id_valid'):
            st.success("✅ ID Valid")
        else:
            st.error("❌ ID Invalid")
    
    st.markdown(f"**Expiry Status:** {output.get('expiry_status', 'Unknown')}")
    st.metric("Confidence", f"{output.get('confidence', 0):.1%}")


def show_decision_output(output: Dict):
    """Display decision output"""
    st.markdown("**Decision Result:**")
    
    decision = output.get('decision', 'pending')
    if decision == 'approved':
        st.success("✅ **APPLICATION APPROVED**")
    elif decision == 'rejected':
        st.error("❌ **APPLICATION REJECTED**")
    else:
        st.warning("⏳ **DECISION PENDING**")
    
    st.metric("Eligibility Score", f"{output.get('eligibility_score', 0):.1%}")
    st.metric("Confidence", f"{output.get('confidence', 0):.1%}")
    
    if 'reasons' in output:
        st.markdown("**Reasons:**")
        for reason in output['reasons']:
            st.markdown(f"- {reason}")


def get_status_color(status: str) -> str:
    """Get color for status display"""
    colors = {
        'pending': '#808080',
        'running': '#FF9800',
        'completed': '#4CAF50',
        'failed': '#F44336',
        'cancelled': '#9E9E9E',
        'timeout': '#FF5722'
    }
    return colors.get(status, '#808080')
