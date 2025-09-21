#!/usr/bin/env python3
"""
Generate test data for the Social Security AI system
"""

import os
import sys
from pathlib import Path
import uuid
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PIL import Image, ImageDraw, ImageFont
import io

# Add app directory to path
current_dir = Path(__file__).parent
app_dir = current_dir.parent.parent
sys.path.insert(0, str(app_dir))

from app.config import settings
from app.shared.database import SessionLocal, init_db
from app.user_management.user_models import User
from app.user_management.user_service import UserService
from app.user_management.auth_schemas import UserCreate
from app.shared.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


def create_test_users():
    """Create test users for the system"""
    db = SessionLocal()
    user_service = UserService()

    test_users = [
        {
            "username": "testuser1",
            "email": "user1@example.com",
            "password": "password123",
            "full_name": "Ahmed Al-Mansouri"
        },
        {
            "username": "testuser2",
            "email": "user2@example.com",
            "password": "password123",
            "full_name": "Fatima Al-Zahra"
        },
        {
            "username": "demo_user",
            "email": "demo@example.com",
            "password": "demo123",
            "full_name": "Demo User"
        }
    ]

    created_users = []

    for user_data in test_users:
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(User.username == user_data["username"]).first()
            if existing_user:
                logger.info(f"User {user_data['username']} already exists")
                created_users.append(existing_user)
                continue

            # Create user
            user_create = UserCreate(
                username=user_data["username"],
                email=user_data["email"],
                password=user_data["password"],
                full_name=user_data["full_name"]
            )
            user = user_service.create_user(db=db, user_data=user_create)
            created_users.append(user)
            logger.info(f"Created test user: {user.username}")

        except Exception as e:
            logger.error(f"Failed to create user {user_data['username']}: {str(e)}")

    db.close()
    return created_users


def generate_bank_statement_pdf(output_path: str, account_holder: str = "Ahmed Al-Mansouri"):
    """Generate a realistic bank statement PDF"""
    try:
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Emirates NBD Bank")
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 70, "Personal Banking Statement")

        # Account details
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, height - 120, "Account Holder:")
        c.setFont("Helvetica", 10)
        c.drawString(150, height - 120, account_holder)

        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, height - 140, "Account Number:")
        c.setFont("Helvetica", 10)
        c.drawString(150, height - 140, "1234567890123456")

        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, height - 160, "Statement Period:")
        c.setFont("Helvetica", 10)
        c.drawString(150, height - 160, "01/01/2024 - 31/01/2024")

        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, height - 180, "Currency:")
        c.setFont("Helvetica", 10)
        c.drawString(150, height - 180, "AED")

        # Account balance
        c.setFont("Helvetica-Bold", 12)
        c.drawString(350, height - 140, "Current Balance:")
        c.setFont("Helvetica-Bold", 14)
        c.drawString(350, height - 160, "AED 15,250.00")

        # Transaction header
        y_pos = height - 220
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y_pos, "Date")
        c.drawString(120, y_pos, "Description")
        c.drawString(350, y_pos, "Debit")
        c.drawString(420, y_pos, "Credit")
        c.drawString(490, y_pos, "Balance")

        # Draw line
        c.line(50, y_pos - 5, 550, y_pos - 5)

        # Transactions
        transactions = [
            ("02/01/2024", "Salary Credit - Emirates Airlines", "", "8,500.00", "15,250.00"),
            ("05/01/2024", "ADCB ATM Withdrawal", "500.00", "", "14,750.00"),
            ("08/01/2024", "DEWA Bill Payment", "280.00", "", "14,470.00"),
            ("12/01/2024", "Grocery - Carrefour", "450.00", "", "14,020.00"),
            ("15/01/2024", "Fuel - ENOC", "120.00", "", "13,900.00"),
            ("20/01/2024", "Transfer from Savings", "", "1,350.00", "15,250.00"),
        ]

        y_pos -= 20
        c.setFont("Helvetica", 9)

        for date, desc, debit, credit, balance in transactions:
            c.drawString(50, y_pos, date)
            c.drawString(120, y_pos, desc)
            c.drawString(350, y_pos, debit)
            c.drawString(420, y_pos, credit)
            c.drawString(490, y_pos, f"AED {balance}")
            y_pos -= 15

        # Summary section
        y_pos -= 30
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y_pos, "Monthly Summary")
        c.line(50, y_pos - 5, 200, y_pos - 5)

        y_pos -= 20
        c.setFont("Helvetica", 9)
        c.drawString(50, y_pos, "Total Credits: AED 9,850.00")
        y_pos -= 15
        c.drawString(50, y_pos, "Total Debits: AED 1,350.00")
        y_pos -= 15
        c.drawString(50, y_pos, "Monthly Income: AED 8,500.00")

        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(50, 50, "This is a computer-generated statement. Emirates NBD Bank PJSC.")

        c.save()
        logger.info(f"Generated bank statement PDF: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate bank statement PDF: {str(e)}")
        return False


def generate_emirates_id_image(output_path: str, name: str = "Ahmed Al-Mansouri"):
    """Generate a mock Emirates ID image"""
    try:
        # Create image
        width, height = 600, 400
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        # Try to use a basic font, fallback to default if not available
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            text_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Background color
        draw.rectangle([(0, 0), (width, height)], fill='#f0f8ff')

        # Header
        draw.rectangle([(0, 0), (width, 60)], fill='#003366')
        draw.text((20, 15), "United Arab Emirates", font=title_font, fill='white')
        draw.text((20, 35), "Emirates Identity Card", font=small_font, fill='white')

        # UAE flag colors (simplified)
        flag_width = 100
        flag_height = 40
        flag_x, flag_y = width - flag_width - 20, 10

        # Red stripe
        draw.rectangle([(flag_x, flag_y), (flag_x + 25, flag_y + flag_height)], fill='red')
        # Green stripe
        draw.rectangle([(flag_x + 25, flag_y), (flag_x + flag_width, flag_y + 13)], fill='green')
        # White stripe
        draw.rectangle([(flag_x + 25, flag_y + 13), (flag_x + flag_width, flag_y + 27)], fill='white')
        # Black stripe
        draw.rectangle([(flag_x + 25, flag_y + 27), (flag_x + flag_width, flag_y + flag_height)], fill='black')

        # Personal Information
        y_offset = 100

        # ID Number
        draw.text((30, y_offset), "ID Number:", font=text_font, fill='black')
        draw.text((150, y_offset), "784-1990-1234567-8", font=text_font, fill='blue')

        # Name
        y_offset += 40
        draw.text((30, y_offset), "Name:", font=text_font, fill='black')
        draw.text((150, y_offset), name, font=text_font, fill='black')

        # Nationality
        y_offset += 40
        draw.text((30, y_offset), "Nationality:", font=text_font, fill='black')
        draw.text((150, y_offset), "United Arab Emirates", font=text_font, fill='black')

        # Date of Birth
        y_offset += 40
        draw.text((30, y_offset), "Date of Birth:", font=text_font, fill='black')
        draw.text((150, y_offset), "01/01/1990", font=text_font, fill='black')

        # Sex
        y_offset += 40
        draw.text((30, y_offset), "Sex:", font=text_font, fill='black')
        draw.text((150, y_offset), "M", font=text_font, fill='black')

        # Expiry Date
        y_offset += 40
        draw.text((30, y_offset), "Expiry Date:", font=text_font, fill='black')
        draw.text((150, y_offset), "01/01/2030", font=text_font, fill='black')

        # Photo placeholder
        photo_x, photo_y = 400, 100
        photo_size = 120
        draw.rectangle([(photo_x, photo_y), (photo_x + photo_size, photo_y + photo_size)],
                      fill='lightgray', outline='black')
        draw.text((photo_x + 30, photo_y + 55), "PHOTO", font=text_font, fill='black')

        # Security features text
        draw.text((30, height - 40), "Security Features: Hologram, RFID Chip", font=small_font, fill='gray')

        # Save image
        img.save(output_path, 'JPEG', quality=95)
        logger.info(f"Generated Emirates ID image: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate Emirates ID image: {str(e)}")
        return False


def setup_test_directories():
    """Create necessary directories for test data"""
    directories = [
        "uploads",
        "uploads/test_data",
        "logs"
    ]

    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")


def main():
    """Main function to generate all test data"""
    logger.info("Starting test data generation")

    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()

        # Setup directories
        setup_test_directories()

        # Create test users
        logger.info("Creating test users...")
        test_users = create_test_users()

        # Generate test documents
        logger.info("Generating test documents...")

        # Bank statement
        bank_statement_path = "uploads/test_data/sample_bank_statement.pdf"
        generate_bank_statement_pdf(bank_statement_path)

        # Emirates ID
        emirates_id_path = "uploads/test_data/sample_emirates_id.jpg"
        generate_emirates_id_image(emirates_id_path)

        logger.info("Test data generation completed successfully!")

        print("\n" + "="*60)
        print("TEST DATA GENERATION COMPLETE")
        print("="*60)
        print(f"Created {len(test_users)} test users:")
        for user in test_users:
            print(f"  - {user.username} ({user.email})")

        print(f"\nGenerated test documents:")
        print(f"  - Bank Statement: {bank_statement_path}")
        print(f"  - Emirates ID: {emirates_id_path}")

        print(f"\nTest credentials:")
        print("  Username: testuser1")
        print("  Password: password123")
        print("\nYou can now test the complete workflow!")

    except Exception as e:
        logger.error(f"Test data generation failed: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()