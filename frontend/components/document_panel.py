"""
Document upload panel component
"""

import streamlit as st
from typing import Dict, Any, Optional
from frontend.utils.api_client import api_client
from frontend.utils.dashboard_state import (
    add_uploaded_document, get_uploaded_document,
    set_error_message, set_success_message, update_processing_status
)


def show_document_panel():
    """Show the document upload panel (center panel)"""
    st.subheader("📄 Document Upload")

    current_app_id = st.session_state.get('current_application_id')

    if not current_app_id:
        show_upload_requirements()
    else:
        show_document_upload_interface()


def show_upload_requirements():
    """Show document requirements when no application exists"""
    st.info("📋 **Please submit your application form first**")

    st.markdown("**Required Documents:**")

    # Bank Statement requirement
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("🏦 **Bank Statement**")
        with col2:
            st.markdown("""
            - Last 3 months bank statement
            - PDF format preferred
            - Maximum size: 50MB
            - Must show income and balance
            """)

    st.markdown("---")

    # Emirates ID requirement
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("🆔 **Emirates ID**")
        with col2:
            st.markdown("""
            - Clear photo or scan of Emirates ID
            - PDF, JPG, or PNG format
            - Maximum size: 50MB
            - Both sides if needed
            """)

    st.markdown("---")
    st.markdown("**💡 Tip:** Complete and submit your application form to enable document upload.")


def show_document_upload_interface():
    """Show document upload interface when application exists"""
    # Bank Statement Upload
    st.markdown("**🏦 Bank Statement**")
    bank_statement_file = st.file_uploader(
        "Upload Bank Statement",
        type=['pdf'],
        key="bank_statement",
        help="Upload your last 3 months bank statement (PDF format, max 50MB)"
    )

    # Show bank statement status
    bank_doc = get_uploaded_document('bank_statement')
    if bank_doc:
        show_document_status('bank_statement', bank_doc)
    elif bank_statement_file:
        # New file uploaded
        if validate_file_upload(bank_statement_file, 'bank_statement'):
            file_content = bank_statement_file.read()
            add_uploaded_document('bank_statement', bank_statement_file.name, file_content)
            set_success_message("📤 Bank statement uploaded successfully!")
            st.rerun()

    st.markdown("---")

    # Emirates ID Upload
    st.markdown("**🆔 Emirates ID**")
    emirates_id_file = st.file_uploader(
        "Upload Emirates ID",
        type=['pdf', 'jpg', 'jpeg', 'png'],
        key="emirates_id",
        help="Upload clear photo or scan of your Emirates ID (PDF/JPG/PNG, max 50MB)"
    )

    # Show emirates ID status
    emirates_doc = get_uploaded_document('emirates_id')
    if emirates_doc:
        show_document_status('emirates_id', emirates_doc)
    elif emirates_id_file:
        # New file uploaded
        if validate_file_upload(emirates_id_file, 'emirates_id'):
            file_content = emirates_id_file.read()
            add_uploaded_document('emirates_id', emirates_id_file.name, file_content)
            set_success_message("📤 Emirates ID uploaded successfully!")
            st.rerun()

    st.markdown("---")

    # Upload status and actions
    show_upload_actions()


def show_document_status(doc_type: str, doc_info: Dict[str, Any]):
    """Show status of uploaded document"""
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown(f"✅ **{doc_info['file_name']}**")
        st.caption(f"Uploaded: {doc_info['uploaded_at'].strftime('%H:%M:%S')}")

    with col2:
        file_size_mb = len(doc_info['file_content']) / (1024 * 1024)
        st.markdown(f"📊 {file_size_mb:.1f}MB")

    with col3:
        if st.button(f"🗑️ Remove", key=f"remove_{doc_type}"):
            remove_document(doc_type)


def show_upload_actions():
    """Show upload actions and status"""
    bank_doc = get_uploaded_document('bank_statement')
    emirates_doc = get_uploaded_document('emirates_id')

    # Upload summary
    uploaded_count = sum([1 for doc in [bank_doc, emirates_doc] if doc is not None])
    st.markdown(f"**📊 Upload Progress: {uploaded_count}/2 documents**")

    if uploaded_count == 0:
        st.info("📤 Upload your documents to start processing")
    elif uploaded_count == 1:
        st.warning("⚠️ Please upload the remaining document")
    else:
        st.success("✅ All documents uploaded!")

    st.markdown("---")

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        # Start processing button
        if uploaded_count > 0:
            if st.button("🚀 Start Processing", use_container_width=True, type="primary"):
                start_document_processing()

    with col2:
        # Clear all button
        if uploaded_count > 0:
            if st.button("🗑️ Clear All", use_container_width=True):
                clear_all_documents()


    # Show processing tips
    if uploaded_count == 2:
        st.markdown("---")
        show_processing_tips()


def show_processing_tips():
    """Show processing tips"""
    with st.expander("💡 Processing Information"):
        st.markdown("""
        **What happens next:**
        1. **Document Scanning** - OCR extraction of text from your documents
        2. **Income Analysis** - AI analysis of your bank statement
        3. **Identity Verification** - Verification of Emirates ID details
        4. **Eligibility Decision** - AI-powered decision making

        **Processing Time:** Typically 1-2 minutes

        **Quality Tips:**
        - Ensure documents are clear and readable
        - Bank statement should show recent transactions
        - Emirates ID should be valid and not expired
        """)


def validate_file_upload(uploaded_file, doc_type: str) -> bool:
    """Validate uploaded file"""
    if not uploaded_file:
        return False

    # Check file size (50MB limit)
    file_size = uploaded_file.size
    max_size = 50 * 1024 * 1024  # 50MB

    if file_size > max_size:
        set_error_message(f"❌ File too large. Maximum size is 50MB (current: {file_size / (1024*1024):.1f}MB)")
        return False

    # Check file type
    file_type = uploaded_file.type
    if doc_type == 'bank_statement':
        allowed_types = ['application/pdf']
        if file_type not in allowed_types:
            set_error_message("❌ Bank statement must be in PDF format")
            return False
    elif doc_type == 'emirates_id':
        allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
        if file_type not in allowed_types:
            set_error_message("❌ Emirates ID must be in PDF, JPG, or PNG format")
            return False

    return True


def start_document_processing():
    """Start document processing by uploading to API"""
    current_app_id = st.session_state.get('current_application_id')
    if not current_app_id:
        set_error_message("❌ No active application found")
        return

    # Prepare files for upload
    files = {}

    bank_doc = get_uploaded_document('bank_statement')
    if bank_doc:
        files['bank_statement'] = bank_doc['file_content']

    emirates_doc = get_uploaded_document('emirates_id')
    if emirates_doc:
        files['emirates_id'] = emirates_doc['file_content']

    if not files:
        set_error_message("❌ No documents to upload")
        return

    with st.spinner("🚀 Uploading documents and starting processing..."):
        # Upload documents
        result = api_client.upload_documents(current_app_id, files)

        if 'error' in result:
            set_error_message(f"❌ Upload failed: {result['error']}")
        else:
            set_success_message("🎉 Documents uploaded! Processing started...")

            # Start processing
            process_result = api_client.start_processing(current_app_id)

            if 'error' not in process_result:
                update_processing_status(process_result)

            st.rerun()


def remove_document(doc_type: str):
    """Remove uploaded document"""
    if doc_type in st.session_state.uploaded_documents:
        del st.session_state.uploaded_documents[doc_type]
        set_success_message(f"🗑️ {doc_type.replace('_', ' ').title()} removed")
        st.rerun()


def clear_all_documents():
    """Clear all uploaded documents"""
    st.session_state.uploaded_documents = {}
    set_success_message("🗑️ All documents cleared")
    st.rerun()


def show_document_analysis_results():
    """Show document analysis results if available"""
    processing_status = st.session_state.get('processing_status')
    if not processing_status:
        return

    partial_results = processing_status.get('partial_results', {})
    if not partial_results:
        return

    st.markdown("---")
    st.markdown("**📊 Analysis Results**")

    # Bank statement analysis
    bank_data = partial_results.get('bank_statement', {})
    if bank_data:
        with st.expander("🏦 Bank Statement Analysis"):
            col1, col2 = st.columns(2)
            with col1:
                if 'monthly_income' in bank_data:
                    st.metric("Monthly Income", f"AED {bank_data['monthly_income']:,.2f}")
                if 'account_balance' in bank_data:
                    st.metric("Account Balance", f"AED {bank_data['account_balance']:,.2f}")
            with col2:
                if 'confidence' in bank_data:
                    confidence = float(bank_data['confidence'])
                    st.metric("Confidence", f"{confidence:.1%}")
                if 'processing_time' in bank_data:
                    st.metric("Processing Time", f"{bank_data['processing_time']} seconds")

    # Emirates ID analysis
    emirates_data = partial_results.get('emirates_id', {})
    if emirates_data:
        with st.expander("🆔 Emirates ID Analysis"):
            col1, col2 = st.columns(2)
            with col1:
                if 'full_name' in emirates_data:
                    st.markdown(f"**Name:** {emirates_data['full_name']}")
                if 'id_number' in emirates_data:
                    st.markdown(f"**ID Number:** {emirates_data['id_number']}")
            with col2:
                if 'confidence' in emirates_data:
                    confidence = float(emirates_data['confidence'])
                    st.metric("Confidence", f"{confidence:.1%}")
                if 'nationality' in emirates_data:
                    st.markdown(f"**Nationality:** {emirates_data['nationality']}")