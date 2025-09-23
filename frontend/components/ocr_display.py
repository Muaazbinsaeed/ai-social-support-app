"""
Enhanced OCR Results Display Component
Provides detailed visualization of OCR results with interactive features
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from frontend.utils.api_client import api_client
from frontend.utils.dashboard_state import get_current_application_id


def show_enhanced_ocr_display():
    """Display enhanced OCR results with interactive features"""
    st.markdown("### 🔍 Enhanced OCR Analysis")

    current_app_id = get_current_application_id()
    if not current_app_id:
        st.info("📋 No application selected. Please submit an application first.")
        return

    # Control buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔄 Refresh OCR Status", width='stretch', key="refresh_ocr"):
            st.rerun()

    with col2:
        if st.button("📊 Enhanced Status", width='stretch', key="enhanced_status"):
            st.session_state.show_enhanced_status = not st.session_state.get('show_enhanced_status', False)

    with col3:
        if st.button("🔧 Manual OCR Trigger", width='stretch', key="manual_ocr"):
            st.session_state.show_manual_ocr = not st.session_state.get('show_manual_ocr', False)

    with col4:
        if st.button("💡 OCR Health Check", width='stretch', key="ocr_health"):
            check_ocr_health()

    # Get processing status
    with st.spinner("Loading OCR status..."):
        if st.session_state.get('show_enhanced_status', False):
            status_result = api_client.get_enhanced_processing_status(current_app_id)
        else:
            status_result = api_client.get_processing_status(current_app_id)

    if 'error' in status_result:
        st.error(f"❌ Failed to load OCR status: {status_result['error']}")
        return

    # Display OCR-specific information
    display_ocr_overview(status_result)

    # Display documents with OCR results
    if status_result.get('documents'):
        display_documents_ocr(status_result['documents'])

    # Manual OCR trigger interface
    if st.session_state.get('show_manual_ocr', False):
        display_manual_ocr_interface()

    # Enhanced status details
    if st.session_state.get('show_enhanced_status', False):
        display_enhanced_status_details(status_result)


def display_ocr_overview(status_data: Dict[str, Any]):
    """Display OCR processing overview"""
    st.markdown("#### 📊 OCR Processing Overview")

    # Calculate OCR-specific metrics
    documents = status_data.get('documents', [])
    total_docs = len(documents)
    ocr_completed = len([doc for doc in documents if doc.get('ocr_status') == 'completed'])
    ocr_in_progress = len([doc for doc in documents if doc.get('ocr_status') == 'in_progress'])
    ocr_failed = len([doc for doc in documents if doc.get('ocr_status') == 'failed'])

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Documents", total_docs)

    with col2:
        st.metric("OCR Completed", ocr_completed, delta=f"{(ocr_completed/max(total_docs, 1)*100):.0f}%")

    with col3:
        if ocr_in_progress > 0:
            st.metric("In Progress", ocr_in_progress, delta="Processing...")
        else:
            st.metric("In Progress", ocr_in_progress)

    with col4:
        if ocr_failed > 0:
            st.metric("Failed", ocr_failed, delta="⚠️", delta_color="inverse")
        else:
            st.metric("Failed", ocr_failed, delta="✅")

    # Overall progress bar
    if total_docs > 0:
        ocr_progress = (ocr_completed / total_docs) * 100
        st.progress(ocr_progress / 100)
        st.caption(f"OCR Progress: {ocr_progress:.1f}% ({ocr_completed}/{total_docs} documents)")


def display_documents_ocr(documents: List[Dict[str, Any]]):
    """Display detailed OCR results for each document"""
    st.markdown("#### 📄 Document OCR Details")

    for doc in documents:
        doc_type = doc.get('document_type', 'unknown').replace('_', ' ').title()
        filename = doc.get('filename', 'Unknown file')
        ocr_status = doc.get('ocr_status', 'not_started')

        # Document container
        with st.expander(f"📄 {doc_type} - {filename}", expanded=(ocr_status == 'completed')):

            # Document status header
            col1, col2, col3 = st.columns(3)

            with col1:
                status_color = get_ocr_status_color(ocr_status)
                st.markdown(f"**Status:** <span style='color: {status_color}'>{ocr_status.replace('_', ' ').title()}</span>",
                           unsafe_allow_html=True)

            with col2:
                confidence = doc.get('ocr_confidence', 0)
                if confidence > 0:
                    confidence_color = get_confidence_color(confidence)
                    st.markdown(f"**Confidence:** <span style='color: {confidence_color}'>{confidence:.1%}</span>",
                               unsafe_allow_html=True)
                else:
                    st.markdown("**Confidence:** Not available")

            with col3:
                doc_id = doc.get('document_id')
                if doc_id and ocr_status != 'completed':
                    if st.button("🚀 Trigger OCR", key=f"trigger_ocr_{doc_id}", width='stretch'):
                        trigger_document_ocr(doc_id)

            # OCR Results Display
            if ocr_status == 'completed' and doc.get('ocr_text'):
                display_ocr_results(doc)
            elif ocr_status == 'in_progress':
                st.info("🔄 OCR processing in progress... Please wait.")
                st.progress(0.5)
            elif ocr_status == 'failed':
                st.error("❌ OCR processing failed.")
                if doc.get('error_message'):
                    st.error(f"Error: {doc['error_message']}")
                # Retry button
                if doc.get('document_id'):
                    if st.button("🔄 Retry OCR", key=f"retry_ocr_{doc['document_id']}", width='stretch'):
                        trigger_document_ocr(doc['document_id'])
            else:
                st.warning("⏳ OCR has not been started yet.")

            # Processing timeline
            if doc.get('processing_timeline'):
                display_processing_timeline(doc['processing_timeline'])


def display_ocr_results(doc: Dict[str, Any]):
    """Display OCR results with enhanced formatting"""
    st.markdown("##### 📝 Extracted Text")

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📄 Raw Text", "🔍 Structured Data", "📊 Analysis"])

    with tab1:
        # Raw OCR text
        ocr_text = doc.get('ocr_text', '')
        if ocr_text:
            st.text_area(
                "OCR Output",
                value=ocr_text,
                height=200,
                disabled=True,
                key=f"ocr_raw_{doc['document_id']}"
            )

            # Text statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Characters", len(ocr_text))
            with col2:
                st.metric("Words", len(ocr_text.split()))
            with col3:
                st.metric("Lines", len(ocr_text.split('\n')))
        else:
            st.info("No text extracted yet.")

    with tab2:
        # Structured extracted data
        extracted_data = doc.get('extracted_data', {})
        if extracted_data:
            display_structured_data(extracted_data, doc['document_type'])
        else:
            st.info("No structured data extracted yet.")

    with tab3:
        # Analysis results
        display_ocr_analysis(doc)


def display_structured_data(extracted_data: Dict[str, Any], document_type: str):
    """Display structured data extraction results"""
    if document_type == 'emirates_id':
        display_emirates_id_data(extracted_data)
    elif document_type == 'bank_statement':
        display_bank_statement_data(extracted_data)
    else:
        st.json(extracted_data)


def display_emirates_id_data(data: Dict[str, Any]):
    """Display Emirates ID specific data"""
    col1, col2 = st.columns(2)

    with col1:
        if 'emirates_id' in data:
            st.success(f"🆔 **Emirates ID:** {data['emirates_id']}")
        if 'name' in data:
            st.info(f"👤 **Name:** {data['name']}")
        if 'date_of_birth' in data:
            st.info(f"📅 **Date of Birth:** {data['date_of_birth']}")

    with col2:
        if 'nationality' in data:
            st.info(f"🌍 **Nationality:** {data['nationality']}")
        if 'expiry_date' in data:
            st.info(f"⏰ **Expiry Date:** {data['expiry_date']}")
        if 'sex' in data:
            st.info(f"⚧ **Gender:** {data['sex']}")


def display_bank_statement_data(data: Dict[str, Any]):
    """Display Bank Statement specific data"""
    col1, col2 = st.columns(2)

    with col1:
        if 'account_number' in data:
            st.success(f"🏦 **Account Number:** {data['account_number']}")
        if 'balance' in data:
            st.metric("💰 Current Balance", f"AED {data['balance']}")

    with col2:
        if 'monthly_income' in data:
            st.metric("📈 Monthly Income", f"AED {data['monthly_income']}")
        if 'bank_name' in data:
            st.info(f"🏛️ **Bank:** {data['bank_name']}")


def display_ocr_analysis(doc: Dict[str, Any]):
    """Display OCR quality analysis"""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 OCR Quality Metrics**")
        confidence = doc.get('ocr_confidence', 0)

        if confidence > 0.8:
            st.success(f"High Quality: {confidence:.1%}")
        elif confidence > 0.6:
            st.warning(f"Medium Quality: {confidence:.1%}")
        else:
            st.error(f"Low Quality: {confidence:.1%}")

    with col2:
        st.markdown("**⚙️ Processing Details**")
        if doc.get('processing_time'):
            st.info(f"Processing Time: {doc['processing_time']:.1f}s")
        if doc.get('ocr_method'):
            st.info(f"OCR Method: {doc['ocr_method']}")


def display_manual_ocr_interface():
    """Display manual OCR trigger interface"""
    st.markdown("#### 🔧 Manual OCR Operations")

    # Direct OCR upload
    uploaded_file = st.file_uploader(
        "Upload file for direct OCR",
        type=['pdf', 'png', 'jpg', 'jpeg'],
        key="direct_ocr_upload"
    )

    if uploaded_file:
        col1, col2 = st.columns(2)

        with col1:
            document_type = st.selectbox(
                "Document Type",
                ["emirates_id", "bank_statement"],
                key="direct_ocr_type"
            )

        with col2:
            if st.button("🚀 Process with OCR", width='stretch', key="process_direct_ocr"):
                process_direct_ocr(uploaded_file, document_type)


def display_enhanced_status_details(status_data: Dict[str, Any]):
    """Display enhanced status information"""
    st.markdown("#### 📈 Enhanced Processing Details")

    with st.expander("🔍 Detailed Status Information", expanded=False):
        st.json(status_data)


def display_processing_timeline(timeline: List[Dict[str, Any]]):
    """Display processing timeline for a document"""
    st.markdown("##### ⏱️ Processing Timeline")

    for i, event in enumerate(timeline):
        col1, col2, col3 = st.columns([1, 3, 2])

        with col1:
            timestamp = datetime.fromisoformat(event.get('timestamp', ''))
            st.caption(timestamp.strftime('%H:%M:%S'))

        with col2:
            event_type = event.get('event_type', 'unknown')
            if event_type == 'ocr_started':
                st.info("🚀 OCR Started")
            elif event_type == 'ocr_completed':
                st.success("✅ OCR Completed")
            elif event_type == 'ocr_failed':
                st.error("❌ OCR Failed")
            else:
                st.info(f"📝 {event_type}")

        with col3:
            if event.get('message'):
                st.caption(event['message'])


def trigger_document_ocr(document_id: str):
    """Trigger OCR processing for a specific document"""
    with st.spinner("Triggering OCR processing..."):
        result = api_client.ocr_document(document_id)

    if 'error' in result:
        st.error(f"❌ Failed to trigger OCR: {result['error']}")
    else:
        st.success("✅ OCR processing started successfully!")
        st.rerun()


def process_direct_ocr(uploaded_file, document_type: str):
    """Process uploaded file with direct OCR"""
    with st.spinner("Processing file with OCR..."):
        file_content = uploaded_file.read()
        result = api_client.direct_ocr(file_content, uploaded_file.name, document_type)

    if 'error' in result:
        st.error(f"❌ OCR processing failed: {result['error']}")
    else:
        st.success("✅ OCR processing completed!")

        # Display results
        if result.get('extracted_text'):
            st.markdown("##### 📝 Extracted Text")
            st.text_area("OCR Result", result['extracted_text'], height=200)

        if result.get('extracted_data'):
            st.markdown("##### 🔍 Extracted Data")
            st.json(result['extracted_data'])


def check_ocr_health():
    """Check OCR service health"""
    with st.spinner("Checking OCR service health..."):
        result = api_client.get_ocr_health()

    if 'error' in result:
        st.error(f"❌ OCR service health check failed: {result['error']}")
    else:
        st.success("✅ OCR service is healthy!")
        if result.get('details'):
            with st.expander("Health Details"):
                st.json(result['details'])


def get_ocr_status_color(status: str) -> str:
    """Get color for OCR status display"""
    colors = {
        'not_started': '#808080',
        'in_progress': '#FF9800',
        'completed': '#4CAF50',
        'failed': '#F44336'
    }
    return colors.get(status, '#808080')


def get_confidence_color(confidence: float) -> str:
    """Get color for confidence display"""
    if confidence >= 0.8:
        return '#4CAF50'  # Green
    elif confidence >= 0.6:
        return '#FF9800'  # Orange
    else:
        return '#F44336'  # Red