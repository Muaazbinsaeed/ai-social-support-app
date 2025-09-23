"""
Enhanced Document Management Panel with full CRUD operations
"""

import streamlit as st
from typing import Dict, Any, Optional
import base64
from datetime import datetime
from frontend.utils.api_client import api_client
from frontend.utils.dashboard_state import (
    set_error_message, set_success_message
)
from frontend.utils.auth_cookies import save_session_to_cookies


class DocumentManager:
    """Manages document operations for the application"""
    
    def __init__(self):
        self.initialize_document_state()
        self.load_documents_from_backend()
    
    def initialize_document_state(self):
        """Initialize document state in session"""
        if 'document_state' not in st.session_state:
            st.session_state.document_state = {
                'bank_statement': None,
                'emirates_id': None
            }
        
        if 'document_metadata' not in st.session_state:
            st.session_state.document_metadata = {
                'bank_statement': {},
                'emirates_id': {}
            }
    
    def load_documents_from_backend(self):
        """Load documents from backend if they exist"""
        # Check if we need to reload documents
        if st.session_state.get('documents_loaded'):
            return
        
        current_app_id = st.session_state.get('current_application_id')
        if not current_app_id:
            return
        
        try:
            # Get document status from backend
            result = api_client.get_documents_status(current_app_id)
            
            if 'error' not in result and result.get('documents'):
                docs = result['documents']
                
                # Load bank statement metadata
                if 'bank_statement' in docs and docs['bank_statement']:
                    bank_doc = docs['bank_statement']
                    st.session_state.document_state['bank_statement'] = {
                        'filename': bank_doc.get('filename', 'bank_statement.pdf'),
                        'uploaded_at': datetime.fromisoformat(bank_doc['uploaded_at']) if bank_doc.get('uploaded_at') else datetime.now(),
                        'size': bank_doc.get('file_size', 0),
                        'status': bank_doc.get('status', 'submitted'),
                        'data': None,  # Will be loaded on demand
                        'document_id': bank_doc.get('id')
                    }
                    st.session_state.document_metadata['bank_statement'] = {
                        'status': bank_doc.get('status', 'submitted'),
                        'document_id': bank_doc.get('id')
                    }
                
                # Load emirates ID metadata
                if 'emirates_id' in docs and docs['emirates_id']:
                    emirates_doc = docs['emirates_id']
                    st.session_state.document_state['emirates_id'] = {
                        'filename': emirates_doc.get('filename', 'emirates_id.jpg'),
                        'uploaded_at': datetime.fromisoformat(emirates_doc['uploaded_at']) if emirates_doc.get('uploaded_at') else datetime.now(),
                        'size': emirates_doc.get('file_size', 0),
                        'status': emirates_doc.get('status', 'submitted'),
                        'data': None,  # Will be loaded on demand
                        'document_id': emirates_doc.get('id')
                    }
                    st.session_state.document_metadata['emirates_id'] = {
                        'status': emirates_doc.get('status', 'submitted'),
                        'document_id': emirates_doc.get('id')
                    }
                
                st.session_state.documents_loaded = True
                
        except Exception as e:
            # Silently fail - documents will be empty
            pass
    
    def get_document(self, doc_type: str) -> Optional[Dict[str, Any]]:
        """Get document from session state"""
        return st.session_state.document_state.get(doc_type)
    
    def add_document(self, doc_type: str, file_data: bytes, filename: str, metadata: Dict = None):
        """Add or update a document"""
        # Store document in session
        st.session_state.document_state[doc_type] = {
            'data': file_data,
            'filename': filename,
            'uploaded_at': datetime.now(),
            'size': len(file_data),
            'status': 'uploaded'
        }
        
        # Store metadata
        st.session_state.document_metadata[doc_type] = metadata or {
            'original_filename': filename,
            'upload_timestamp': datetime.now().isoformat(),
            'file_size': len(file_data),
            'status': 'pending_processing'
        }
        
        # Reset application status if documents were previously submitted/processed
        current_state = st.session_state.get('processing_status', {}).get('current_state', 'draft')
        if current_state not in ['draft', 'form_submitted', 'documents_uploaded']:
            # Reset status to documents_uploaded since documents changed
            st.session_state.processing_status = {
                'current_state': 'documents_uploaded',
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'message': 'Documents updated - please re-submit for processing'
            }
        
        # Save to cookies for persistence
        save_session_to_cookies()
        
        return True
    
    def delete_document(self, doc_type: str) -> bool:
        """Delete a document"""
        if doc_type in st.session_state.document_state:
            st.session_state.document_state[doc_type] = None
            st.session_state.document_metadata[doc_type] = {}
            save_session_to_cookies()
            return True
        return False
    
    def reset_document_status(self, doc_type: str) -> bool:
        """Reset document status to allow re-upload"""
        if doc_type in st.session_state.document_state and st.session_state.document_state[doc_type]:
            st.session_state.document_state[doc_type]['status'] = 'reset'
            st.session_state.document_metadata[doc_type]['status'] = 'pending_reupload'
            save_session_to_cookies()
            return True
        return False
    
    def update_document_metadata(self, doc_type: str, metadata: Dict[str, Any]):
        """Update document metadata"""
        if doc_type in st.session_state.document_metadata:
            st.session_state.document_metadata[doc_type].update(metadata)
            save_session_to_cookies()
    
    def can_edit_document(self, doc_type: str) -> bool:
        """Check if document can be edited"""
        doc = self.get_document(doc_type)
        if not doc:
            return True  # Can add new document
        
        status = doc.get('status', 'uploaded')
        # Can edit if status is uploaded, submitted, reset, or error
        # Submitted documents can be replaced before processing starts
        return status in ['uploaded', 'submitted', 'reset', 'error', 'pending_reupload']
    
    def get_document_status_color(self, status: str) -> str:
        """Get color for document status"""
        status_colors = {
            'uploaded': '🟢',
            'processing': '🟡',
            'processed': '✅',
            'error': '🔴',
            'reset': '🔄',
            'pending_reupload': '🟠'
        }
        return status_colors.get(status, '⚪')


def show_enhanced_document_panel():
    """Show enhanced document management panel"""
    st.subheader("📄 Document Management")
    
    doc_manager = DocumentManager()
    current_app_id = st.session_state.get('current_application_id')
    
    if not current_app_id:
        show_document_requirements()
        return
    
    # Create tabs for each document type
    tab1, tab2 = st.tabs(["🏦 Bank Statement", "🆔 Emirates ID"])
    
    with tab1:
        manage_document('bank_statement', doc_manager)
    
    with tab2:
        manage_document('emirates_id', doc_manager)
    
    # Show overall document status
    st.markdown("---")
    show_document_summary(doc_manager)


def manage_document(doc_type: str, doc_manager: DocumentManager):
    """Manage individual document"""
    doc = doc_manager.get_document(doc_type)
    doc_metadata = st.session_state.document_metadata.get(doc_type, {})
    
    # Document type specific settings
    if doc_type == 'bank_statement':
        allowed_types = ['pdf']
        doc_label = "Bank Statement"
        doc_icon = "🏦"
        requirements = """
        - Last 3 months statement
        - PDF format only
        - Maximum 50MB
        - Must show income and balance
        """
    else:  # emirates_id
        allowed_types = ['pdf', 'jpg', 'jpeg', 'png']
        doc_label = "Emirates ID"
        doc_icon = "🆔"
        requirements = """
        - Clear photo or scan
        - PDF, JPG, or PNG format
        - Maximum 50MB
        - Both sides if applicable
        """
    
    # Show current document status
    if doc:
        show_document_card(doc, doc_type, doc_manager, doc_label, doc_icon)
    else:
        show_upload_interface(doc_type, doc_manager, allowed_types, doc_label, requirements)


def show_document_card(doc: Dict[str, Any], doc_type: str, doc_manager: DocumentManager, label: str, icon: str):
    """Show uploaded document card with actions"""
    status = doc.get('status', 'uploaded')
    status_icon = doc_manager.get_document_status_color(status)
    
    # Show preview if requested
    show_document_preview(doc, doc_type)
    
    # Document info card
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 2])
        
        with col1:
            st.markdown(f"**{icon} {label}**")
            st.caption(f"📄 {doc['filename']}")
            st.caption(f"📊 Size: {doc['size'] / 1024:.1f} KB")
            st.caption(f"📅 Uploaded: {doc['uploaded_at'].strftime('%Y-%m-%d %H:%M')}")
        
        with col2:
            st.markdown(f"**Status**")
            st.markdown(f"{status_icon} {status.title()}")
        
        with col3:
            st.markdown("**Actions**")
            
            # Action buttons based on status
            can_edit = doc_manager.can_edit_document(doc_type)
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                if can_edit:
                    if st.button("✏️ Replace", key=f"edit_{doc_type}", width='stretch'):
                        st.session_state[f"replacing_{doc_type}"] = True
                        st.rerun()
                
                if st.button("👁️ View", key=f"view_{doc_type}", width='stretch'):
                    st.session_state[f"show_preview_{doc_type}"] = True
                    st.rerun()
            
            with col_b:
                if status in ['processed', 'processing']:
                    if st.button("🔄 Reset", key=f"reset_{doc_type}", width='stretch'):
                        if doc_manager.reset_document_status(doc_type):
                            st.success(f"✅ {label} status reset. You can now replace it.")
                            st.rerun()
                
                if can_edit:
                    if st.button("🗑️ Delete", key=f"delete_{doc_type}", width='stretch'):
                        if st.session_state.get(f"confirm_delete_{doc_type}"):
                            if doc_manager.delete_document(doc_type):
                                st.success(f"✅ {label} deleted successfully!")
                                st.session_state[f"confirm_delete_{doc_type}"] = False
                                st.rerun()
                        else:
                            st.session_state[f"confirm_delete_{doc_type}"] = True
                            st.warning("⚠️ Click Delete again to confirm")
    
    # Show replace interface if replacing
    if st.session_state.get(f"replacing_{doc_type}"):
        st.markdown("---")
        st.info(f"📝 **Replace {label}**")
        
        new_file = st.file_uploader(
            f"Upload new {label}",
            type=['pdf'] if doc_type == 'bank_statement' else ['pdf', 'jpg', 'jpeg', 'png'],
            key=f"replace_upload_{doc_type}"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Confirm Replace", key=f"confirm_replace_{doc_type}", width='stretch'):
                if new_file:
                    file_data = new_file.read()
                    if validate_document(file_data, new_file.name, doc_type):
                        doc_manager.add_document(doc_type, file_data, new_file.name)
                        st.session_state[f"replacing_{doc_type}"] = False
                        st.success(f"✅ {label} replaced successfully!")
                        st.rerun()
                else:
                    st.error("Please select a file to upload")
        
        with col2:
            if st.button("❌ Cancel", key=f"cancel_replace_{doc_type}", width='stretch'):
                st.session_state[f"replacing_{doc_type}"] = False
                st.rerun()


def show_upload_interface(doc_type: str, doc_manager: DocumentManager, allowed_types: list, label: str, requirements: str):
    """Show upload interface for new document"""
    st.info(f"📤 **Upload {label}**")
    
    # Show requirements
    with st.expander("📋 Requirements", expanded=False):
        st.markdown(requirements)
    
    # File uploader
    uploaded_file = st.file_uploader(
        f"Choose {label}",
        type=allowed_types,
        key=f"upload_{doc_type}",
        help=f"Upload your {label} document"
    )
    
    if uploaded_file:
        # Validate and save
        file_data = uploaded_file.read()
        
        if validate_document(file_data, uploaded_file.name, doc_type):
            # Show preview before saving
            st.markdown("**Preview:**")
            if uploaded_file.type == "application/pdf":
                st.info(f"📄 PDF Document: {uploaded_file.name} ({len(file_data)/1024:.1f} KB)")
            else:
                st.image(file_data, caption=uploaded_file.name, width='stretch')
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"✅ Save {label}", key=f"save_{doc_type}", type="primary", width='stretch'):
                    if doc_manager.add_document(doc_type, file_data, uploaded_file.name):
                        st.success(f"✅ {label} uploaded successfully!")

                        # Auto-preview OCR option
                        if st.session_state.get('auto_ocr_preview', False):
                            with st.spinner("🔍 Running automatic OCR preview..."):
                                ocr_result = api_client.direct_ocr(file_data, uploaded_file.name, doc_type)
                                if 'error' not in ocr_result:
                                    st.info(f"🎯 OCR Preview: Found {len(ocr_result.get('extracted_text', ''))} characters with {ocr_result.get('confidence_average', 0):.1%} confidence")

                        st.rerun()

            with col2:
                if st.button("❌ Cancel", key=f"cancel_upload_{doc_type}", width='stretch'):
                    st.rerun()

            # Auto-OCR option
            st.checkbox("🔍 Auto-run OCR preview after upload", key='auto_ocr_preview',
                       help="Automatically run OCR analysis after successful upload for quick verification")


def validate_document(file_data: bytes, filename: str, doc_type: str) -> bool:
    """Validate document before upload"""
    # Check file size (50MB max)
    max_size = 50 * 1024 * 1024  # 50MB
    if len(file_data) > max_size:
        st.error(f"❌ File too large. Maximum size is 50MB.")
        return False
    
    # Check file extension
    valid_extensions = {
        'bank_statement': ['.pdf'],
        'emirates_id': ['.pdf', '.jpg', '.jpeg', '.png']
    }
    
    file_ext = filename.lower().split('.')[-1]
    allowed_exts = valid_extensions.get(doc_type, [])
    
    if f".{file_ext}" not in allowed_exts:
        st.error(f"❌ Invalid file type. Allowed types: {', '.join(allowed_exts)}")
        return False
    
    return True


def show_document_preview(doc: Dict[str, Any], doc_type: str):
    """Show document preview in modal"""
    # Create a unique key for the preview
    preview_key = f"preview_{doc_type}_{datetime.now().timestamp()}"
    
    # Show in a dialog/modal style
    if st.session_state.get(f"show_preview_{doc_type}", False):
        st.markdown("### 👁️ Document Preview")
        st.markdown(f"**File:** {doc['filename']}")
        st.markdown(f"**Size:** {doc.get('size', 0) / 1024:.1f} KB")
        
        # Load document data if not already loaded
        doc_data = doc.get('data')
        if not doc_data and doc.get('document_id'):
            # Try to download from backend
            with st.spinner("Loading document..."):
                result = api_client.download_document(doc['document_id'])
                if 'error' not in result and result.get('data'):
                    # Decode base64 data
                    import base64
                    doc_data = base64.b64decode(result['data'])
                    doc['data'] = doc_data  # Cache for future use
                else:
                    st.error(f"Failed to load document: {result.get('error', 'Document not found')}")
                    doc_data = None
        
        if doc_data:
            if doc['filename'].lower().endswith('.pdf'):
                st.info("📄 PDF Document")
                # Offer download button
                st.download_button(
                    label="📥 Download PDF",
                    data=doc_data,
                    file_name=doc['filename'],
                    mime="application/pdf",
                    key=f"download_{preview_key}"
                )
            else:
                # Show image preview
                try:
                    st.image(doc_data, caption=doc['filename'], width='stretch')
                except Exception as e:
                    st.error(f"Cannot display image: {str(e)}")
                    # Offer download as fallback
                    st.download_button(
                        label="📥 Download Image",
                        data=doc_data,
                        file_name=doc['filename'],
                        mime="image/jpeg",
                        key=f"download_img_{preview_key}"
                    )
        else:
            # Try to load document data if we have a document_id
            if doc.get('document_id'):
                if st.button("🔄 Load Document", key=f"load_{preview_key}"):
                    with st.spinner("Loading document from server..."):
                        result = api_client.download_document(doc['document_id'])
                        if 'error' not in result and result.get('data'):
                            import base64
                            doc_data = base64.b64decode(result['data'])
                            doc['data'] = doc_data  # Cache for future use
                            st.rerun()
                        else:
                            st.error(f"Failed to load document: {result.get('error', 'Unknown error')}")
                st.info("📥 Document is stored on server. Click 'Load Document' to view.")
            else:
                st.warning("Document data not available. It may need to be re-uploaded.")
        
        if st.button("✅ Close Preview", key=f"close_{preview_key}"):
            st.session_state[f"show_preview_{doc_type}"] = False
            st.rerun()


def show_document_summary(doc_manager: DocumentManager):
    """Show overall document status summary"""
    bank_doc = doc_manager.get_document('bank_statement')
    emirates_doc = doc_manager.get_document('emirates_id')
    
    # Count available documents (either uploaded or loaded from backend)
    uploaded_count = sum([1 for doc in [bank_doc, emirates_doc] if doc is not None])
    
    # Status summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📊 Documents", f"{uploaded_count}/2")
    
    with col2:
        if uploaded_count == 2:
            st.success("✅ All Ready")
        elif uploaded_count == 1:
            st.warning("⚠️ 1 Missing")
        else:
            st.info("📤 Upload Required")
    
    with col3:
        # Submit and Process buttons
        if uploaded_count == 2:
            current_app_id = st.session_state.get('current_application_id')
            
            # Check document status
            both_submitted = (bank_doc and bank_doc.get('status') in ['submitted', 'processing', 'processed'] and 
                            emirates_doc and emirates_doc.get('status') in ['submitted', 'processing', 'processed'])
            
            both_processed = (bank_doc and bank_doc.get('status') in ['processing', 'processed'] and 
                            emirates_doc and emirates_doc.get('status') in ['processing', 'processed'])
            
            if not both_submitted:
                # Show submit button for newly uploaded documents
                if st.button("💾 Submit Documents", type="primary", width='stretch'):
                    submit_documents_to_backend(current_app_id, doc_manager)
            elif not both_processed:
                # Show process button if documents are submitted but not processed
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🚀 Process Documents", type="primary", width='stretch'):
                        process_documents(current_app_id, doc_manager)
                with col2:
                    if st.button("🔍 Quick OCR Preview", width='stretch'):
                        show_quick_ocr_preview(doc_manager)
            else:
                # Documents are already processed
                st.success("✅ Documents processed successfully!")


def submit_documents_to_backend(app_id: str, doc_manager: DocumentManager):
    """Submit documents to backend for storage"""
    bank_doc = doc_manager.get_document('bank_statement')
    emirates_doc = doc_manager.get_document('emirates_id')
    
    if not bank_doc or not emirates_doc:
        st.error("❌ Please upload both documents before submitting")
        return
    
    # Check if already submitted and processed
    if bank_doc.get('status') in ['processing', 'processed'] and emirates_doc.get('status') in ['processing', 'processed']:
        st.info("ℹ️ Documents are already being processed or have been processed.")
        return
    
    # Check if already submitted
    if bank_doc.get('status') == 'submitted' and emirates_doc.get('status') == 'submitted':
        st.success("✅ Documents are already submitted! You can now process them.")
        return
    
    # Check if document data is available
    if not bank_doc.get('data') or not emirates_doc.get('data'):
        # Try to load from backend if documents were previously submitted
        if bank_doc.get('document_id') and emirates_doc.get('document_id'):
            with st.spinner("Loading documents from server..."):
                # Load bank statement
                bank_result = api_client.download_document(bank_doc['document_id'])
                if 'error' not in bank_result and bank_result.get('data'):
                    import base64
                    bank_doc['data'] = base64.b64decode(bank_result['data'])
                
                # Load Emirates ID
                emirates_result = api_client.download_document(emirates_doc['document_id'])
                if 'error' not in emirates_result and emirates_result.get('data'):
                    import base64
                    emirates_doc['data'] = base64.b64decode(emirates_result['data'])
        
        # Check again after trying to load
        if not bank_doc.get('data') or not emirates_doc.get('data'):
            st.error("❌ Document data not available. Please re-upload the documents.")
            return
    
    with st.spinner("📤 Submitting documents..."):
        # Prepare files for upload
        files = {
            'bank_statement': (bank_doc['filename'], bank_doc['data'], 'application/pdf'),
            'emirates_id': (emirates_doc['filename'], emirates_doc['data'], 
                          'application/pdf' if emirates_doc['filename'].lower().endswith('.pdf') else 'image/jpeg')
        }
        
        # Call API to save documents
        result = api_client.upload_documents(app_id, files)
        
        if 'error' not in result:
            # Update document status to submitted
            bank_doc['status'] = 'submitted'
            emirates_doc['status'] = 'submitted'
            doc_manager.update_document_metadata('bank_statement', {'status': 'submitted'})
            doc_manager.update_document_metadata('emirates_id', {'status': 'submitted'})
            
            st.success("✅ Documents submitted and saved successfully!")
            st.info("📋 Documents are now stored. Click 'Process Documents' when ready to start processing.")
            
            # Save to session
            save_session_to_cookies()
            st.rerun()
        else:
            st.error(f"❌ Failed to submit documents: {result['error']}")


def process_documents(app_id: str, doc_manager: DocumentManager):
    """Start processing submitted documents with OCR integration"""
    bank_doc = doc_manager.get_document('bank_statement')
    emirates_doc = doc_manager.get_document('emirates_id')

    if not bank_doc or not emirates_doc:
        st.error("❌ No documents to process")
        return

    if bank_doc.get('status') != 'submitted' or emirates_doc.get('status') != 'submitted':
        st.warning("⚠️ Please submit documents first before processing")
        return

    # Enhanced processing with OCR preview option
    st.markdown("### 🚀 Document Processing Options")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("⚡ Quick Process", type="primary", width='stretch', help="Start processing immediately"):
            _start_document_processing(app_id, doc_manager, skip_ocr_preview=True)

    with col2:
        if st.button("🔍 Process with OCR Preview", width='stretch', help="Run OCR analysis first, then process"):
            _start_document_processing(app_id, doc_manager, skip_ocr_preview=False)


def _start_document_processing(app_id: str, doc_manager: DocumentManager, skip_ocr_preview: bool = True):
    """Internal function to start document processing"""
    bank_doc = doc_manager.get_document('bank_statement')
    emirates_doc = doc_manager.get_document('emirates_id')

    if not skip_ocr_preview:
        st.markdown("#### 🔍 OCR Analysis Preview")

        # Run OCR on both documents for preview
        docs_to_process = [
            ('bank_statement', bank_doc, '🏦 Bank Statement'),
            ('emirates_id', emirates_doc, '🆔 Emirates ID')
        ]

        ocr_results = {}
        for doc_type, doc, label in docs_to_process:
            file_data = doc.get('data')
            if file_data:
                with st.spinner(f"Analyzing {label}..."):
                    ocr_result = api_client.direct_ocr(file_data, doc['filename'], doc_type)
                    if 'error' not in ocr_result:
                        ocr_results[doc_type] = ocr_result
                        with st.expander(f"📄 {label} OCR Results", expanded=False):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Confidence", f"{ocr_result.get('confidence_average', 0):.1%}")
                            with col2:
                                st.metric("Text Length", len(ocr_result.get('extracted_text', '')))
                            with col3:
                                st.metric("Processing Time", f"{ocr_result.get('processing_time_ms', 0)}ms")

                            if ocr_result.get('extracted_text'):
                                st.text_area("Extracted Text",
                                           value=ocr_result['extracted_text'][:500] + ("..." if len(ocr_result['extracted_text']) > 500 else ""),
                                           height=100, disabled=True)
                    else:
                        st.error(f"❌ OCR failed for {label}: {ocr_result['error']}")

        st.markdown("---")

        if ocr_results:
            st.success(f"✅ OCR analysis completed for {len(ocr_results)} documents")

            if st.button("🚀 Continue with Processing", type="primary", width='stretch'):
                _execute_backend_processing(app_id, doc_manager)
        else:
            st.error("❌ OCR analysis failed. Cannot proceed with processing.")
    else:
        _execute_backend_processing(app_id, doc_manager)


def _execute_backend_processing(app_id: str, doc_manager: DocumentManager):
    """Execute the backend processing workflow"""
    with st.spinner("🔄 Starting document processing..."):
        # Start processing
        process_result = api_client.process_application(app_id)

        if 'error' not in process_result:
            # Update status to processing
            bank_doc = doc_manager.get_document('bank_statement')
            emirates_doc = doc_manager.get_document('emirates_id')

            bank_doc['status'] = 'processing'
            emirates_doc['status'] = 'processing'
            doc_manager.update_document_metadata('bank_statement', {'status': 'processing'})
            doc_manager.update_document_metadata('emirates_id', {'status': 'processing'})

            st.success("🚀 Document processing started!")
            st.info("⏳ Processing may take a few minutes. Check the Processing Status panel for real-time updates.")

            # Save to session
            save_session_to_cookies()
            st.rerun()
        else:
            st.error(f"❌ Failed to start processing: {process_result['error']}")


def show_document_requirements():
    """Show document requirements when no application exists"""
    st.info("📋 **Please submit your application form first**")
    
    st.markdown("### Required Documents")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏦 Bank Statement")
        st.markdown("""
        - Last 3 months statement
        - PDF format only
        - Maximum 50MB
        - Must show:
          - Account holder name
          - Monthly income
          - Current balance
          - Transaction history
        """)
    
    with col2:
        st.markdown("#### 🆔 Emirates ID")
        st.markdown("""
        - Clear photo or scan
        - Accepted formats: PDF, JPG, PNG
        - Maximum 50MB
        - Requirements:
          - Both sides (if applicable)
          - Clearly visible text
          - No glare or shadows
          - Valid (not expired)
        """)
    
    st.markdown("---")
    st.info("💡 **Tip:** Complete and submit your application form in the left panel to enable document upload.")


def show_quick_ocr_preview(doc_manager: DocumentManager):
    """Show quick OCR preview for uploaded documents"""
    st.markdown("### 🔍 Quick OCR Preview")

    # Select document to preview
    doc_type = st.selectbox(
        "Select document to preview:",
        ["bank_statement", "emirates_id"],
        format_func=lambda x: "📄 Bank Statement" if x == "bank_statement" else "🆔 Emirates ID"
    )

    doc = doc_manager.get_document(doc_type)
    if not doc:
        st.warning(f"⚠️ No {doc_type.replace('_', ' ')} uploaded yet.")
        return

    # Check if document data is available
    file_data = doc.get('data')
    if not file_data and doc.get('document_id'):
        st.info("📥 Document is stored on server. Loading for OCR preview...")
        with st.spinner("Loading document from server..."):
            download_result = api_client.download_document(doc['document_id'])
            if 'error' not in download_result and download_result.get('data'):
                import base64
                file_data = base64.b64decode(download_result['data'])
                # Cache in session for future use
                doc['data'] = file_data
            else:
                st.error(f"❌ Failed to load document: {download_result.get('error', 'Unknown error')}")
                return

    if not file_data:
        st.error("❌ Document data not available. Please re-upload the document.")
        return

    if st.button(f"🚀 Run OCR on {doc_type.replace('_', ' ').title()}", width='stretch'):
        with st.spinner("Processing document with OCR..."):
            filename = doc['filename']

            # Use direct OCR API for preview
            result = api_client.direct_ocr(file_data, filename, doc_type)

        if 'error' in result:
            st.error(f"❌ OCR failed: {result['error']}")
        else:
            st.success("✅ OCR processing completed!")

            # Display results
            if result.get('extracted_text'):
                st.markdown("#### 📝 Extracted Text")
                with st.expander("View OCR Text", expanded=True):
                    st.text_area(
                        "OCR Result",
                        value=result['extracted_text'],
                        height=200,
                        disabled=True
                    )

                    # Quick stats
                    text = result['extracted_text']
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Characters", len(text))
                    with col2:
                        st.metric("Words", len(text.split()))
                    with col3:
                        st.metric("Lines", len(text.split('\n')))

            if result.get('extracted_data'):
                st.markdown("#### 🔍 Structured Data")
                with st.expander("View Extracted Data", expanded=True):
                    if doc_type == 'emirates_id':
                        display_emirates_preview(result['extracted_data'])
                    elif doc_type == 'bank_statement':
                        display_bank_preview(result['extracted_data'])

            if result.get('confidence'):
                st.markdown("#### 📊 Quality Assessment")
                confidence = result['confidence']
                if confidence >= 0.8:
                    st.success(f"🎉 High Quality: {confidence:.1%}")
                elif confidence >= 0.6:
                    st.warning(f"⚠️ Medium Quality: {confidence:.1%}")
                else:
                    st.error(f"❌ Low Quality: {confidence:.1%}")


def display_emirates_preview(data: dict):
    """Display Emirates ID preview data"""
    col1, col2 = st.columns(2)

    with col1:
        if 'emirates_id' in data:
            st.info(f"🆔 **ID Number:** {data['emirates_id']}")
        if 'name' in data:
            st.info(f"👤 **Name:** {data['name']}")

    with col2:
        if 'date_of_birth' in data:
            st.info(f"📅 **DOB:** {data['date_of_birth']}")
        if 'nationality' in data:
            st.info(f"🌍 **Nationality:** {data['nationality']}")


def display_bank_preview(data: dict):
    """Display Bank Statement preview data"""
    col1, col2 = st.columns(2)

    with col1:
        if 'account_number' in data:
            st.info(f"🏦 **Account:** {data['account_number']}")
        if 'balance' in data:
            st.metric("💰 Balance", f"AED {data['balance']}")

    with col2:
        if 'monthly_income' in data:
            st.metric("📈 Income", f"AED {data['monthly_income']}")
        if 'bank_name' in data:
            st.info(f"🏛️ **Bank:** {data['bank_name']}")
