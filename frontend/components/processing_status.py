"""
Processing Status Display Component
Shows detailed status of document processing including OCR results
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional
from frontend.utils.api_client import api_client
from frontend.utils.dashboard_state import get_current_application_id


def show_processing_status():
    """Display detailed processing status with OCR results"""
    current_app_id = get_current_application_id()
    
    if not current_app_id:
        st.info("📋 No application selected. Please submit an application first.")
        return
    
    # Add refresh button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 🔄 Document Processing Status")
    with col2:
        if st.button("🔄 Refresh Status", use_container_width=True, key="refresh_processing_status"):
            st.rerun()
    
    # Get detailed processing status
    with st.spinner("Loading processing status..."):
        status_result = api_client.get_processing_status(current_app_id)
    
    if 'error' in status_result:
        if status_result.get('status_code') == 404:
            st.info("📋 No application found or documents haven't been processed yet.")
            st.markdown("**Next Steps:**")
            st.markdown("1. Fill out the application form")
            st.markdown("2. Upload your documents")
            st.markdown("3. Submit documents to backend")
            st.markdown("4. Click 'Process Documents'")
        else:
            st.error(f"❌ Failed to load status: {status_result['error']}")
        return
    
    # Display overall status
    show_overall_status(status_result)
    
    # Display document processing details
    if status_result.get('documents'):
        show_document_processing(status_result['documents'])
    
    # Display workflow steps
    if status_result.get('workflow_steps'):
        show_workflow_steps(status_result['workflow_steps'])


def show_overall_status(status_data: Dict[str, Any]):
    """Display overall application status"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status = status_data.get('overall_status', 'unknown')
        status_color = get_status_color(status)
        st.markdown(f"**Status:** <span style='color: {status_color}'>{status.replace('_', ' ').title()}</span>", unsafe_allow_html=True)
    
    with col2:
        progress = status_data.get('progress', 0)
        st.metric("Progress", f"{progress}%")
    
    with col3:
        if status_data.get('processing_started'):
            started = datetime.fromisoformat(status_data['processing_started'].replace('Z', '+00:00'))
            elapsed = datetime.now() - started.replace(tzinfo=None)
            st.metric("Processing Time", f"{elapsed.seconds // 60}m {elapsed.seconds % 60}s")
    
    # Progress bar
    st.progress(progress / 100)


def show_document_processing(documents: list):
    """Display document processing details with OCR results"""
    st.markdown("### 📄 Document Processing Details")
    
    for doc in documents:
        with st.expander(f"📄 {doc['document_type'].replace('_', ' ').title()} - {doc['filename']}", expanded=True):
            # Document status
            col1, col2, col3 = st.columns(3)
            
            with col1:
                doc_status = doc.get('status', 'unknown')
                status_color = get_status_color(doc_status)
                st.markdown(f"**Document Status:** <span style='color: {status_color}'>{doc_status}</span>", unsafe_allow_html=True)
            
            with col2:
                ocr_status = doc.get('ocr_status', 'not_started')
                ocr_color = get_ocr_status_color(ocr_status)
                st.markdown(f"**OCR Status:** <span style='color: {ocr_color}'>{ocr_status.replace('_', ' ').title()}</span>", unsafe_allow_html=True)
            
            with col3:
                confidence = doc.get('ocr_confidence', 0)
                if confidence > 0:
                    st.metric("OCR Confidence", f"{confidence:.1%}")
            
            # OCR Text Preview
            if doc.get('ocr_text'):
                st.markdown("#### 📝 Extracted Text Preview")
                with st.container():
                    st.text_area(
                        "OCR Output",
                        value=doc['ocr_text'],
                        height=150,
                        disabled=True,
                        key=f"ocr_text_{doc['document_id']}"
                    )
            
            # Extracted Data
            if doc.get('extracted_data'):
                st.markdown("#### 🔍 Extracted Information")
                extracted = doc['extracted_data']
                
                if doc['document_type'] == 'emirates_id':
                    col1, col2 = st.columns(2)
                    with col1:
                        if 'emirates_id' in extracted:
                            st.info(f"**Emirates ID:** {extracted['emirates_id']}")
                    with col2:
                        if 'name' in extracted:
                            st.info(f"**Name:** {extracted['name']}")
                
                elif doc['document_type'] == 'bank_statement':
                    col1, col2 = st.columns(2)
                    with col1:
                        if 'account_number' in extracted:
                            st.info(f"**Account Number:** {extracted['account_number']}")
                    with col2:
                        if 'balance' in extracted:
                            st.info(f"**Balance:** AED {extracted['balance']}")
            
            # Processing messages
            if ocr_status == 'in_progress':
                st.info("🔄 OCR processing in progress... Please wait.")
            elif ocr_status == 'failed':
                st.error("❌ OCR processing failed. Please try re-uploading the document.")
            elif ocr_status == 'not_started':
                st.warning("⏳ OCR processing has not started yet.")


def show_workflow_steps(steps: list):
    """Display workflow processing steps"""
    st.markdown("### 📊 Processing Steps Timeline")
    
    if not steps:
        st.info("No processing steps recorded yet.")
        return
    
    # Create timeline
    for i, step in enumerate(steps):
        col1, col2, col3 = st.columns([1, 3, 2])
        
        with col1:
            # Step number and status icon
            status = step.get('status', 'pending')
            if status == 'completed':
                st.success(f"✅ Step {i+1}")
            elif status == 'in_progress':
                st.info(f"🔄 Step {i+1}")
            elif status == 'failed':
                st.error(f"❌ Step {i+1}")
            else:
                st.warning(f"⏳ Step {i+1}")
        
        with col2:
            # Step details
            st.markdown(f"**{step['step_name'].replace('_', ' ').title()}**")
            st.caption(step.get('message', 'No message'))
        
        with col3:
            # Timing
            if step.get('created_at'):
                created = datetime.fromisoformat(step['created_at'])
                st.caption(f"Started: {created.strftime('%H:%M:%S')}")
            
            if step.get('completed_at'):
                completed = datetime.fromisoformat(step['completed_at'])
                duration = (completed - created).total_seconds()
                st.caption(f"Duration: {duration:.1f}s")
        
        if i < len(steps) - 1:
            st.markdown("---")


def get_status_color(status: str) -> str:
    """Get color for status display"""
    status_colors = {
        'draft': '#808080',
        'form_submitted': '#4CAF50',
        'documents_uploaded': '#2196F3',
        'scanning_documents': '#FF9800',
        'ocr_completed': '#4CAF50',
        'analyzing_income': '#FF9800',
        'analyzing_identity': '#FF9800',
        'analysis_completed': '#4CAF50',
        'making_decision': '#FF9800',
        'decision_completed': '#4CAF50',
        'approved': '#4CAF50',
        'rejected': '#F44336',
        'needs_review': '#FF9800',
        'processing': '#FF9800',
        'completed': '#4CAF50',
        'failed': '#F44336'
    }
    return status_colors.get(status, '#808080')


def get_ocr_status_color(status: str) -> str:
    """Get color for OCR status display"""
    ocr_colors = {
        'not_started': '#808080',
        'in_progress': '#FF9800',
        'completed': '#4CAF50',
        'failed': '#F44336'
    }
    return ocr_colors.get(status, '#808080')
