#!/usr/bin/env python3
"""
Generate synthetic test data for development and testing
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.logging_config import setup_logging, get_logger
from app.config import settings

# Setup logging
setup_logging()
logger = get_logger(__name__)


def create_sample_bank_statement_pdf():
    """Create a sample bank statement PDF for testing"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch

        # Create uploads directory if it doesn't exist
        upload_dir = Path(settings.upload_dir)
        test_dir = upload_dir / "test_documents"
        test_dir.mkdir(parents=True, exist_ok=True)

        # Sample bank statement data
        bank_statement_data = {
            "bank_name": "Emirates NBD Bank",
            "account_holder": "Ahmed Ali Hassan",
            "account_number": "1234567890123456",
            "emirates_id": "784-1990-1234567-8",
            "statement_period": "November 2024",
            "opening_balance": 15250.00,
            "closing_balance": 22292.75,
            "transactions": [
                {"date": "01/11/2024", "description": "Salary Credit - Emirates Airlines", "amount": "+8,500.00"},
                {"date": "02/11/2024", "description": "Online Transfer to Savings", "amount": "-1,000.00"},
                {"date": "05/11/2024", "description": "Carrefour Supermarket", "amount": "-156.75"},
                {"date": "07/11/2024", "description": "ADNOC Fuel Payment", "amount": "-180.00"},
                {"date": "10/11/2024", "description": "DEWA Electricity Bill", "amount": "-420.50"},
                {"date": "12/11/2024", "description": "ATM Withdrawal - Mall of Emirates", "amount": "-500.00"},
                {"date": "15/11/2024", "description": "Online Shopping - Noon.com", "amount": "-245.30"},
                {"date": "18/11/2024", "description": "Restaurant Payment - Marina Walk", "amount": "-89.25"},
                {"date": "20/11/2024", "description": "Salik Toll Payment", "amount": "-12.00"},
                {"date": "22/11/2024", "description": "Pharmacy - Life Pharmacy", "amount": "-67.50"},
                {"date": "25/11/2024", "description": "Metro Card Top-up", "amount": "-50.00"},
                {"date": "28/11/2024", "description": "Internet Bill - Etisalat", "amount": "-299.00"},
                {"date": "30/11/2024", "description": "Grocery Shopping - Spinneys", "amount": "-123.45"},
            ]
        }

        # Create PDF file
        pdf_path = test_dir / "sample_bank_statement.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

        # Container for the 'Flowable' objects
        story = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )

        # Title
        story.append(Paragraph(f"<b>{bank_statement_data['bank_name']}</b>", title_style))
        story.append(Paragraph("<b>ACCOUNT STATEMENT</b>", title_style))
        story.append(Spacer(1, 20))

        # Account Information
        account_info = [
            ["Account Holder:", bank_statement_data['account_holder']],
            ["Account Number:", bank_statement_data['account_number']],
            ["Emirates ID:", bank_statement_data['emirates_id']],
            ["Statement Period:", bank_statement_data['statement_period']],
            ["Opening Balance:", f"AED {bank_statement_data['opening_balance']:,.2f}"],
            ["Closing Balance:", f"AED {bank_statement_data['closing_balance']:,.2f}"],
        ]

        account_table = Table(account_info, colWidths=[2*inch, 3*inch])
        account_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))

        story.append(account_table)
        story.append(Spacer(1, 30))

        # Transactions
        story.append(Paragraph("<b>TRANSACTION HISTORY</b>", styles['Heading2']))
        story.append(Spacer(1, 12))

        # Transaction table headers
        transaction_data = [["Date", "Description", "Amount"]]

        # Add transactions
        for transaction in bank_statement_data['transactions']:
            transaction_data.append([
                transaction['date'],
                transaction['description'],
                transaction['amount']
            ])

        # Create transaction table
        transaction_table = Table(transaction_data, colWidths=[1.2*inch, 3.5*inch, 1.3*inch])
        transaction_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),  # Right align amounts
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        story.append(transaction_table)
        story.append(Spacer(1, 30))

        # Footer
        footer_text = f"Statement generated on {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/>This is an electronically generated statement."
        story.append(Paragraph(footer_text, styles['Normal']))

        # Build PDF
        doc.build(story)

        logger.info(f"Sample bank statement PDF created: {pdf_path}")
        return str(pdf_path)

    except ImportError:
        logger.warning("ReportLab not available, creating simple text-based PDF")
        return create_simple_bank_statement_text(test_dir)
    except Exception as e:
        logger.error(f"Failed to create bank statement PDF: {str(e)}")
        return create_simple_bank_statement_text(test_dir)


def create_simple_bank_statement_text(test_dir: Path):
    """Create a simple text-based bank statement if PDF libraries are not available"""
    try:
        # Create a simple text file that can be treated as a document
        txt_path = test_dir / "sample_bank_statement.txt"

        bank_statement_content = f"""
EMIRATES NBD BANK
ACCOUNT STATEMENT

=====================================

Account Holder: Ahmed Ali Hassan
Account Number: 1234567890123456
Emirates ID: 784-1990-1234567-8
Statement Period: November 2024

Opening Balance: AED 15,250.00
Closing Balance: AED 22,292.75

=====================================
TRANSACTION HISTORY
=====================================

Date        Description                    Amount
01/11/2024  Salary Credit - Emirates      +8,500.00
02/11/2024  Transfer to Savings           -1,000.00
05/11/2024  Carrefour Supermarket          -156.75
07/11/2024  ADNOC Fuel Payment             -180.00
10/11/2024  DEWA Electricity Bill          -420.50
12/11/2024  ATM Withdrawal                 -500.00
15/11/2024  Online Shopping - Noon         -245.30
18/11/2024  Restaurant Payment              -89.25
20/11/2024  Salik Toll Payment              -12.00
22/11/2024  Pharmacy Purchase               -67.50
25/11/2024  Metro Card Top-up               -50.00
28/11/2024  Internet Bill - Etisalat       -299.00
30/11/2024  Grocery Shopping               -123.45

=====================================

Monthly Income Analysis:
Primary Income: AED 8,500.00 (Salary)
Total Credits: AED 8,500.00
Total Debits: AED 3,143.75
Net Movement: AED 5,356.25

Statement generated on {datetime.now().strftime('%d/%m/%Y %H:%M')}
This is an electronically generated statement.
"""

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(bank_statement_content)

        logger.info(f"Sample bank statement text file created: {txt_path}")
        return str(txt_path)

    except Exception as e:
        logger.error(f"Failed to create bank statement text file: {str(e)}")
        return None


def create_sample_emirates_id_image():
    """Create a sample Emirates ID image for testing"""
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Create uploads directory if it doesn't exist
        upload_dir = Path(settings.upload_dir)
        test_dir = upload_dir / "test_documents"
        test_dir.mkdir(parents=True, exist_ok=True)

        # Create a simple Emirates ID mockup
        img_width, img_height = 800, 500
        img = Image.new('RGB', (img_width, img_height), color='lightblue')
        draw = ImageDraw.Draw(img)

        # Try to use default font
        try:
            font_large = ImageFont.truetype("arial.ttf", 24)
            font_medium = ImageFont.truetype("arial.ttf", 18)
            font_small = ImageFont.truetype("arial.ttf", 14)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Draw Emirates ID content
        draw.text((50, 30), "UNITED ARAB EMIRATES", fill='darkblue', font=font_large)
        draw.text((50, 70), "IDENTITY CARD", fill='darkblue', font=font_medium)

        # Personal information
        draw.text((50, 150), "Name: Ahmed Ali Hassan", fill='black', font=font_medium)
        draw.text((50, 180), "Nationality: United Arab Emirates", fill='black', font=font_small)
        draw.text((50, 210), "Identity No: 784-1990-1234567-8", fill='black', font=font_medium)
        draw.text((50, 240), "Date of Birth: 15/03/1990", fill='black', font=font_small)
        draw.text((50, 270), "Sex: M", fill='black', font=font_small)
        draw.text((50, 300), "Date of Issue: 12/01/2020", fill='black', font=font_small)
        draw.text((50, 330), "Date of Expiry: 11/01/2030", fill='black', font=font_small)

        # Add some design elements
        draw.rectangle([30, 30, img_width-30, img_height-30], outline='darkblue', width=3)
        draw.rectangle([40, 40, img_width-40, img_height-40], outline='lightblue', width=1)

        # Add UAE flag colors as decoration
        draw.rectangle([600, 50, 750, 100], fill='red')
        draw.rectangle([600, 100, 750, 150], fill='green')
        draw.rectangle([600, 150, 750, 200], fill='black')

        # Save the image
        img_path = test_dir / "sample_emirates_id.jpg"
        img.save(img_path, 'JPEG', quality=95)

        logger.info(f"Sample Emirates ID image created: {img_path}")
        return str(img_path)

    except ImportError:
        logger.warning("PIL not available, creating simple text-based Emirates ID")
        return create_simple_emirates_id_text(test_dir)
    except Exception as e:
        logger.error(f"Failed to create Emirates ID image: {str(e)}")
        return create_simple_emirates_id_text(test_dir)


def create_simple_emirates_id_text(test_dir: Path):
    """Create a simple text-based Emirates ID if image libraries are not available"""
    try:
        txt_path = test_dir / "sample_emirates_id.txt"

        emirates_id_content = f"""
UNITED ARAB EMIRATES
IDENTITY CARD

=====================================

Name: Ahmed Ali Hassan
Nationality: United Arab Emirates
Identity No: 784-1990-1234567-8
Date of Birth: 15/03/1990
Sex: M
Date of Issue: 12/01/2020
Date of Expiry: 11/01/2030

=====================================

This is a sample Emirates ID document
for testing purposes only.

Document created on {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(emirates_id_content)

        logger.info(f"Sample Emirates ID text file created: {txt_path}")
        return str(txt_path)

    except Exception as e:
        logger.error(f"Failed to create Emirates ID text file: {str(e)}")
        return None


def create_sample_applications():
    """Create sample application scenarios for testing"""
    scenarios = [
        {
            "name": "High Income - Should be Rejected",
            "full_name": "Mohammad Ahmed Sultan",
            "emirates_id": "784-1985-9876543-2",
            "phone": "+971501111111",
            "email": "mohammad@example.com",
            "monthly_income": 12000,
            "account_balance": 85000,
            "expected_outcome": "rejected"
        },
        {
            "name": "Low Income - Should be Approved",
            "full_name": "Fatima Ali Hassan",
            "emirates_id": "784-1992-1111222-3",
            "phone": "+971502222222",
            "email": "fatima@example.com",
            "monthly_income": 2500,
            "account_balance": 5000,
            "expected_outcome": "approved"
        },
        {
            "name": "Borderline Income - Should Need Review",
            "full_name": "Omar Khalil Ahmed",
            "emirates_id": "784-1988-3333444-5",
            "phone": "+971503333333",
            "email": "omar@example.com",
            "monthly_income": 3900,
            "account_balance": 8500,
            "expected_outcome": "needs_review"
        },
        {
            "name": "Standard Case - Should be Approved",
            "full_name": "Ahmed Ali Hassan",
            "emirates_id": "784-1990-1234567-8",
            "phone": "+971501234567",
            "email": "ahmed@example.com",
            "monthly_income": 3200,
            "account_balance": 12000,
            "expected_outcome": "approved"
        }
    ]

    return scenarios


def main():
    """Generate all test data"""
    try:
        logger.info("Starting test data generation...")

        # Create test documents
        logger.info("Creating sample bank statement...")
        bank_statement_path = create_sample_bank_statement_pdf()

        logger.info("Creating sample Emirates ID...")
        emirates_id_path = create_sample_emirates_id_image()

        # Create sample application scenarios
        scenarios = create_sample_applications()

        # Create summary file
        upload_dir = Path(settings.upload_dir)
        test_dir = upload_dir / "test_documents"
        summary_path = test_dir / "test_data_summary.txt"

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("SOCIAL SECURITY AI - TEST DATA SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("SAMPLE DOCUMENTS:\n")
            f.write("-" * 20 + "\n")
            if bank_statement_path:
                f.write(f"Bank Statement: {bank_statement_path}\n")
            if emirates_id_path:
                f.write(f"Emirates ID: {emirates_id_path}\n")
            f.write("\n")

            f.write("SAMPLE APPLICATION SCENARIOS:\n")
            f.write("-" * 30 + "\n")
            for i, scenario in enumerate(scenarios, 1):
                f.write(f"{i}. {scenario['name']}\n")
                f.write(f"   Name: {scenario['full_name']}\n")
                f.write(f"   Emirates ID: {scenario['emirates_id']}\n")
                f.write(f"   Expected Outcome: {scenario['expected_outcome']}\n")
                f.write(f"   Monthly Income: AED {scenario['monthly_income']:,.2f}\n")
                f.write(f"   Account Balance: AED {scenario['account_balance']:,.2f}\n\n")

            f.write("USAGE INSTRUCTIONS:\n")
            f.write("-" * 20 + "\n")
            f.write("1. Start the application: docker-compose up\n")
            f.write("2. Access dashboard: http://localhost:8005\n")
            f.write("3. Login with test credentials: user1 / password123\n")
            f.write("4. Use the sample application data above\n")
            f.write("5. Upload the generated sample documents\n")
            f.write("6. Test different scenarios to see various outcomes\n\n")

            f.write("TESTING SCENARIOS:\n")
            f.write("-" * 18 + "\n")
            f.write("- Test successful processing with standard case\n")
            f.write("- Test rejection with high income case\n")
            f.write("- Test manual review with borderline case\n")
            f.write("- Test error handling by uploading invalid files\n")
            f.write("- Test graceful failure by stopping AI services\n")

        logger.info("Test data generation completed successfully!")

        print("\n" + "="*60)
        print("TEST DATA GENERATION COMPLETED")
        print("="*60)
        print(f"📁 Test documents created in: {test_dir}")
        print(f"📄 Summary file: {summary_path}")
        print("\n📋 Sample Application Scenarios:")
        for i, scenario in enumerate(scenarios, 1):
            print(f"  {i}. {scenario['name']}")
            print(f"     Expected: {scenario['expected_outcome'].upper()}")

        print("\n🚀 Ready for testing!")
        print("   1. Start system: docker-compose up")
        print("   2. Access dashboard: http://localhost:8005")
        print("   3. Login: user1 / password123")
        print("   4. Use sample data for testing")
        print("="*60)

    except Exception as e:
        logger.error(f"Test data generation failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()