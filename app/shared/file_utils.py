"""
File handling utilities
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import uuid
import mimetypes

from app.config import settings
from app.shared.exceptions import FileStorageError, ValidationError
from app.shared.logging_config import get_logger

logger = get_logger(__name__)


class FileManager:
    """File management utilities for document handling"""

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension from filename"""
        return Path(filename).suffix.lower()

    @staticmethod
    def generate_secure_filename(original_filename: str, application_id: str) -> str:
        """Generate a secure filename with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = FileManager.get_file_extension(original_filename)
        safe_name = Path(original_filename).stem[:50]  # Limit length
        return f"{safe_name}_{timestamp}{extension}"

    @staticmethod
    def get_upload_path(application_id: str, filename: str) -> Path:
        """Get the full upload path for a file"""
        upload_dir = Path(settings.upload_dir)
        app_dir = upload_dir / str(application_id)
        return app_dir / filename

    @staticmethod
    def ensure_upload_directory(application_id: str) -> Path:
        """Ensure upload directory exists for an application"""
        upload_dir = Path(settings.upload_dir)
        app_dir = upload_dir / str(application_id)
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir

    @staticmethod
    def validate_file_type(filename: str) -> bool:
        """Validate file type against allowed extensions"""
        extension = FileManager.get_file_extension(filename)[1:]  # Remove the dot
        return extension in settings.allowed_extensions

    @staticmethod
    def validate_file_size(file_size: int) -> bool:
        """Validate file size against maximum allowed"""
        return file_size <= settings.max_file_size

    @staticmethod
    def get_mime_type(filename: str) -> str:
        """Get MIME type for a file"""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"

    @staticmethod
    def save_uploaded_file(file_content: bytes, application_id: str,
                          original_filename: str) -> tuple[str, str]:
        """
        Save uploaded file to disk
        Returns: (file_path, secure_filename)
        """
        try:
            # Validate file type
            if not FileManager.validate_file_type(original_filename):
                raise ValidationError(
                    f"File type not allowed. Allowed types: {', '.join(settings.allowed_extensions)}",
                    "INVALID_FILE_TYPE"
                )

            # Validate file size
            if not FileManager.validate_file_size(len(file_content)):
                max_mb = settings.max_file_size / (1024 * 1024)
                raise ValidationError(
                    f"File too large. Maximum size: {max_mb:.1f}MB",
                    "FILE_TOO_LARGE"
                )

            # Ensure directory exists
            FileManager.ensure_upload_directory(application_id)

            # Generate secure filename
            secure_filename = FileManager.generate_secure_filename(original_filename, application_id)
            file_path = FileManager.get_upload_path(application_id, secure_filename)

            # Save file
            with open(file_path, "wb") as f:
                f.write(file_content)

            logger.info(
                "File saved successfully",
                application_id=application_id,
                original_filename=original_filename,
                secure_filename=secure_filename,
                file_size=len(file_content)
            )

            return str(file_path), secure_filename

        except (OSError, IOError) as e:
            logger.error("Failed to save file", error=str(e), application_id=application_id)
            raise FileStorageError(f"Failed to save file: {str(e)}", "FILE_SAVE_ERROR")

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete a file from disk"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("File deleted successfully", file_path=file_path)
                return True
            else:
                logger.warning("File not found for deletion", file_path=file_path)
                return False
        except OSError as e:
            logger.error("Failed to delete file", error=str(e), file_path=file_path)
            raise FileStorageError(f"Failed to delete file: {str(e)}", "FILE_DELETE_ERROR")

    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """Get file information"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileStorageError("File not found", "FILE_NOT_FOUND")

            stat = path.stat()
            return {
                "filename": path.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "mime_type": FileManager.get_mime_type(path.name),
                "extension": path.suffix.lower()
            }
        except OSError as e:
            logger.error("Failed to get file info", error=str(e), file_path=file_path)
            raise FileStorageError(f"Failed to get file info: {str(e)}", "FILE_INFO_ERROR")

    @staticmethod
    def cleanup_old_files(days_old: int = 30) -> int:
        """Clean up files older than specified days"""
        try:
            upload_dir = Path(settings.upload_dir)
            if not upload_dir.exists():
                return 0

            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            deleted_count = 0

            for file_path in upload_dir.rglob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except OSError:
                        logger.warning("Failed to delete old file", file_path=str(file_path))

            logger.info(f"Cleanup completed, deleted {deleted_count} old files")
            return deleted_count

        except Exception as e:
            logger.error("Failed to cleanup old files", error=str(e))
            raise FileStorageError(f"Cleanup failed: {str(e)}", "CLEANUP_ERROR")

    @staticmethod
    def get_directory_size(directory: str) -> int:
        """Get total size of directory in bytes"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            return total_size
        except OSError as e:
            logger.error("Failed to calculate directory size", error=str(e))
            return 0