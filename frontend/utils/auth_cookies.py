"""
Authentication cookie management for login persistence
"""

import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Cookie configuration
COOKIE_KEY = "social_security_auth"
COOKIE_PASSWORD = "your-super-secure-cookie-key-for-auth-persistence"
COOKIE_EXPIRY_DAYS = 7


class AuthCookieManager:
    """Manages authentication cookies for login persistence"""

    def __init__(self):
        """Initialize cookie manager"""
        # Initialize with a unique key per session
        if 'cookie_manager' not in st.session_state:
            self.cookies = EncryptedCookieManager(
                prefix="social_security_",
                password=COOKIE_PASSWORD
            )
            
            # Wait for cookies to be ready
            if not self.cookies.ready():
                st.stop()
                
            st.session_state.cookie_manager = self.cookies
        else:
            self.cookies = st.session_state.cookie_manager

    def save_auth_data(self, access_token: str, user_info: Dict[str, Any]) -> None:
        """Save authentication data to cookies"""
        try:
            auth_data = {
                "access_token": access_token,
                "user_info": user_info,
                "timestamp": datetime.now().isoformat(),
                "expires": (datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)).isoformat()
            }

            # Save to encrypted cookie
            self.cookies[COOKIE_KEY] = json.dumps(auth_data)
            self.cookies.save()

        except Exception as e:
            st.error(f"Failed to save authentication data: {str(e)}")
    
    def save_session_data(self, session_data: Dict[str, Any]) -> None:
        """Save full session data including application and documents"""
        try:
            session_data["timestamp"] = datetime.now().isoformat()
            session_data["expires"] = (datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)).isoformat()
            
            # Save session data separately
            self.cookies["session_data"] = json.dumps(session_data)
            self.cookies.save()
        except Exception as e:
            pass  # Silently fail for session data
    
    def load_session_data(self) -> Optional[Dict[str, Any]]:
        """Load full session data"""
        try:
            session_str = self.cookies.get("session_data")
            if not session_str:
                return None
            
            session_data = json.loads(session_str)
            
            # Check expiry
            expires_str = session_data.get("expires")
            if expires_str:
                expires = datetime.fromisoformat(expires_str)
                if datetime.now() > expires:
                    return None
            
            return session_data
        except Exception:
            return None

    def load_auth_data(self) -> Optional[Dict[str, Any]]:
        """Load authentication data from cookies"""
        try:
            auth_data_str = self.cookies.get(COOKIE_KEY)
            if not auth_data_str:
                return None

            auth_data = json.loads(auth_data_str)

            # Check if token has expired
            expires_str = auth_data.get("expires")
            if expires_str:
                expires = datetime.fromisoformat(expires_str)
                if datetime.now() > expires:
                    self.clear_auth_data()
                    return None

            return auth_data

        except Exception as e:
            # Clear invalid cookie data
            self.clear_auth_data()
            return None

    def clear_auth_data(self) -> None:
        """Clear authentication data from cookies"""
        try:
            if COOKIE_KEY in self.cookies:
                del self.cookies[COOKIE_KEY]
            if "session_data" in self.cookies:
                del self.cookies["session_data"]
            self.cookies.save()
        except Exception:
            pass

    def is_auth_valid(self) -> bool:
        """Check if authentication data exists and is valid"""
        auth_data = self.load_auth_data()
        return auth_data is not None and auth_data.get("access_token") is not None


def initialize_auth_from_cookies():
    """Initialize authentication state from cookies if available"""
    try:
        cookie_manager = AuthCookieManager()
        auth_data = cookie_manager.load_auth_data()
        session_data = cookie_manager.load_session_data()

        if auth_data:
            # Restore authentication state
            st.session_state.access_token = auth_data.get("access_token")
            st.session_state.user_info = auth_data.get("user_info")
            st.session_state.is_authenticated = True
            st.session_state.show_login = False
            
            # Restore session data if available
            if session_data:
                restore_session_data(session_data)
            
            return True

        return False

    except Exception:
        return False


def restore_session_data(session_data: Dict[str, Any]):
    """Restore full session data from cookies"""
    try:
        # Restore application data
        if "current_application_id" in session_data:
            st.session_state.current_application_id = session_data["current_application_id"]
        if "application_form_data" in session_data:
            st.session_state.application_form_data = session_data["application_form_data"]
        if "processing_status" in session_data:
            st.session_state.processing_status = session_data["processing_status"]
        
        # Restore document metadata (not actual files)
        if "document_state_meta" in session_data:
            # Initialize document state if not exists
            if 'document_state' not in st.session_state:
                st.session_state.document_state = {}
            
            # Mark documents as needing reload from server
            for doc_type, meta in session_data["document_state_meta"].items():
                if meta:
                    st.session_state.document_state[doc_type] = {
                        'filename': meta.get('filename'),
                        'uploaded_at': datetime.fromisoformat(meta['uploaded_at']) if meta.get('uploaded_at') else None,
                        'size': meta.get('size'),
                        'status': meta.get('status'),
                        'needs_reload': True  # Flag to reload from server
                    }
        
        if "document_metadata" in session_data:
            st.session_state.document_metadata = session_data["document_metadata"]
            
    except Exception:
        pass


def save_auth_to_cookies(access_token: str, user_info: Dict[str, Any]):
    """Save authentication data to cookies"""
    try:
        cookie_manager = AuthCookieManager()
        cookie_manager.save_auth_data(access_token, user_info)
    except Exception:
        pass


def clear_auth_cookies():
    """Clear authentication cookies"""
    try:
        cookie_manager = AuthCookieManager()
        cookie_manager.clear_auth_data()
    except Exception:
        pass


def save_session_to_cookies():
    """Save current session state to cookies for persistence"""
    try:
        cookie_manager = AuthCookieManager()
        
        # Prepare session data (exclude binary data for documents)
        document_state = st.session_state.get("document_state", {})
        document_metadata = st.session_state.get("document_metadata", {})
        
        # Save only metadata, not actual file data (too large for cookies)
        clean_doc_state = {}
        for doc_type, doc in document_state.items():
            if doc:
                clean_doc_state[doc_type] = {
                    'filename': doc.get('filename'),
                    'uploaded_at': doc.get('uploaded_at').isoformat() if doc.get('uploaded_at') else None,
                    'size': doc.get('size'),
                    'status': doc.get('status')
                }
        
        session_data = {
            "current_application_id": st.session_state.get("current_application_id"),
            "application_form_data": st.session_state.get("application_form_data", {}),
            "processing_status": st.session_state.get("processing_status"),
            "document_state_meta": clean_doc_state,
            "document_metadata": document_metadata
        }
        
        # Save to cookies
        cookie_manager.save_session_data(session_data)
    except Exception as e:
        pass  # Silently fail to avoid disrupting the app