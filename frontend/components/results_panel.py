"""
Results panel component for displaying application decisions
"""

import streamlit as st
from typing import Dict, Any
from datetime import datetime
from frontend.utils.dashboard_state import reset_application_state, set_success_message


def show_results_panel():
    """Show the results panel when decision is complete"""
    application_results = st.session_state.get('application_results')

    if not application_results:
        return

    decision = application_results.get('decision', {})
    outcome = decision.get('outcome', 'unknown')

    if outcome == 'approved':
        show_approval_results(decision)
    elif outcome == 'rejected':
        show_rejection_results(decision)
    elif outcome == 'needs_review':
        show_review_required_results(decision)
    else:
        show_unknown_results(decision)

    # Show action buttons
    show_result_actions()


def show_approval_results(decision: Dict[str, Any]):
    """Show approval results"""
    st.success("🎉 **CONGRATULATIONS! Your application has been APPROVED**")

    # Main approval info
    col1, col2, col3 = st.columns(3)

    with col1:
        benefit_amount = decision.get('benefit_amount', 0)
        currency = decision.get('currency', 'AED')
        frequency = decision.get('frequency', 'monthly')
        st.metric(
            "Benefit Amount",
            f"{currency} {benefit_amount:,.0f}/{frequency}",
            help="Your approved monthly benefit amount"
        )

    with col2:
        confidence = decision.get('confidence_score', 0)
        st.metric(
            "Confidence Score",
            f"{float(confidence):.1%}",
            help="AI system confidence in this decision"
        )

    with col3:
        effective_date = decision.get('effective_date')
        if effective_date:
            eff_date = datetime.fromisoformat(effective_date.replace('Z', '+00:00'))
            st.metric(
                "Effective Date",
                eff_date.strftime('%b %d, %Y'),
                help="When your benefits will start"
            )

    st.markdown("---")

    # Reasoning
    reasoning = decision.get('reasoning', {})
    if reasoning:
        show_decision_reasoning(reasoning, 'approved')

    st.markdown("---")

    # Next steps
    next_steps = decision.get('next_steps', [])
    if next_steps:
        st.markdown("**📋 Next Steps:**")
        for i, step in enumerate(next_steps, 1):
            st.markdown(f"{i}. {step}")
    else:
        st.markdown("**📋 Next Steps:**")
        st.markdown("1. Visit your local social security office within 7 days")
        st.markdown("2. Bring original documents for verification")
        st.markdown("3. Set up direct deposit for benefit payments")
        st.markdown("4. Attend mandatory orientation session")

    # Contact info
    show_contact_information()


def show_rejection_results(decision: Dict[str, Any]):
    """Show rejection results"""
    st.error("❌ **Your application has been REJECTED**")

    # Confidence score
    confidence = decision.get('confidence_score', 0)
    st.metric(
        "Decision Confidence",
        f"{float(confidence):.1%}",
        help="AI system confidence in this decision"
    )

    st.markdown("---")

    # Reasoning
    reasoning = decision.get('reasoning', {})
    if reasoning:
        show_decision_reasoning(reasoning, 'rejected')

    st.markdown("---")

    # Appeal process
    st.markdown("**⚖️ Appeal Process:**")
    appeal_deadline = decision.get('appeal_deadline')
    if appeal_deadline:
        deadline = datetime.fromisoformat(appeal_deadline.replace('Z', '+00:00'))
        st.markdown(f"- **Appeal Deadline:** {deadline.strftime('%B %d, %Y')}")
    else:
        st.markdown("- **Appeal Deadline:** 30 days from decision date")

    st.markdown("- **Process:** Submit written appeal with supporting documents")
    st.markdown("- **Contact:** appeals@socialsecurity.gov.ae")
    st.markdown("- **Required:** Additional documentation or clarification")

    # Contact info
    show_contact_information()


def show_review_required_results(decision: Dict[str, Any]):
    """Show manual review required results"""
    st.warning("👀 **MANUAL REVIEW REQUIRED**")

    st.markdown("Your application requires additional review by our team.")

    # Confidence score
    confidence = decision.get('confidence_score', 0)
    st.metric(
        "Initial Assessment Confidence",
        f"{float(confidence):.1%}",
        help="AI system confidence in preliminary assessment"
    )

    st.markdown("---")

    # Reasoning
    reasoning = decision.get('reasoning', {})
    if reasoning:
        show_decision_reasoning(reasoning, 'needs_review')

    st.markdown("---")

    # Review process
    st.markdown("**🔍 Review Process:**")
    review_date = decision.get('review_date')
    if review_date:
        review_dt = datetime.fromisoformat(review_date.replace('Z', '+00:00'))
        st.markdown(f"- **Expected Review Date:** {review_dt.strftime('%B %d, %Y')}")
    else:
        st.markdown("- **Expected Review Time:** 5-10 business days")

    st.markdown("- **Process:** Human expert will review your application")
    st.markdown("- **Notification:** You will be contacted with the final decision")
    st.markdown("- **Required Action:** None - we will contact you")

    # Contact info
    show_contact_information()


def show_unknown_results(decision: Dict[str, Any]):
    """Show unknown/error results"""
    st.error("⚠️ **PROCESSING INCOMPLETE**")
    st.markdown("We encountered an issue processing your application.")

    # Show available information
    confidence = decision.get('confidence_score')
    if confidence:
        st.metric("Processing Confidence", f"{float(confidence):.1%}")

    reasoning = decision.get('reasoning', {})
    if reasoning:
        show_decision_reasoning(reasoning, 'unknown')

    st.markdown("---")
    st.markdown("**📞 Please contact support for assistance:**")
    show_contact_information()


def show_decision_reasoning(reasoning: Dict[str, Any], outcome: str):
    """Show decision reasoning details"""
    with st.expander("🔍 **Decision Reasoning**", expanded=outcome != 'approved'):
        # Summary
        summary = reasoning.get('summary')
        if summary:
            st.markdown(f"**Summary:** {summary}")
            st.markdown("---")

        # Income analysis
        income_analysis = reasoning.get('income_analysis')
        if income_analysis:
            st.markdown("**💰 Income Analysis:**")
            st.markdown(income_analysis)

        # Document verification
        doc_verification = reasoning.get('document_verification')
        if doc_verification:
            st.markdown("**📄 Document Verification:**")
            st.markdown(doc_verification)

        # Risk assessment
        risk_assessment = reasoning.get('risk_assessment')
        if risk_assessment:
            st.markdown("**⚠️ Risk Assessment:**")
            st.markdown(risk_assessment)

        # Eligibility factors
        eligibility_factors = reasoning.get('eligibility_factors', {})
        if eligibility_factors:
            st.markdown("**📊 Eligibility Factors:**")
            col1, col2 = st.columns(2)

            with col1:
                income_eligible = eligibility_factors.get('income_eligible')
                if income_eligible is not None:
                    status = "✅ Yes" if income_eligible else "❌ No"
                    st.markdown(f"- **Income Eligible:** {status}")

                docs_verified = eligibility_factors.get('documents_verified')
                if docs_verified is not None:
                    status = "✅ Yes" if docs_verified else "❌ No"
                    st.markdown(f"- **Documents Verified:** {status}")

            with col2:
                overall_score = eligibility_factors.get('overall_score')
                if overall_score is not None:
                    st.markdown(f"- **Overall Score:** {float(overall_score):.3f}")

                risk_level = eligibility_factors.get('risk_level')
                if risk_level:
                    st.markdown(f"- **Risk Level:** {risk_level}")


def show_contact_information():
    """Show contact information"""
    st.markdown("---")
    st.markdown("**📞 Contact Information:**")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Office Address:**")
        st.markdown("Social Security Office")
        st.markdown("Dubai Government Centre")
        st.markdown("Dubai, UAE")

        st.markdown("**Phone:** +971-4-123-4567")

    with col2:
        st.markdown("**Email Support:**")
        st.markdown("support@socialsecurity.gov.ae")
        st.markdown("appeals@socialsecurity.gov.ae")

        st.markdown("**Office Hours:**")
        st.markdown("Sunday - Thursday: 8:00 AM - 4:00 PM")


def show_result_actions():
    """Show action buttons for results"""
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📋 Download Certificate", use_container_width=True):
            download_certificate()

    with col2:
        if st.button("🖨️ Print Results", use_container_width=True):
            print_results()

    with col3:
        if st.button("💬 Chat Support", use_container_width=True):
            show_chat_support()

    # New application button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🆕 Start New Application", use_container_width=True, type="primary"):
            start_new_application()


def download_certificate():
    """Generate and download certificate"""
    application_results = st.session_state.get('application_results', {})
    decision = application_results.get('decision', {})

    if decision.get('outcome') == 'approved':
        # Generate certificate content
        certificate_content = generate_certificate_content(decision)

        # Create download button
        st.download_button(
            label="📋 Download Certificate (PDF)",
            data=certificate_content,
            file_name=f"social_security_certificate_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            help="Download your approval certificate"
        )

        st.success("✅ Certificate ready for download!")
    else:
        st.warning("⚠️ Certificate only available for approved applications")


def generate_certificate_content(decision: Dict[str, Any]) -> str:
    """Generate certificate content"""
    current_app_id = st.session_state.get('current_application_id', 'N/A')
    user_info = st.session_state.get('user_info', {})
    form_data = st.session_state.get('application_form_data', {})

    benefit_amount = decision.get('benefit_amount', 0)
    currency = decision.get('currency', 'AED')
    effective_date = decision.get('effective_date', '')

    certificate = f"""
UNITED ARAB EMIRATES
SOCIAL SECURITY ADMINISTRATION
BENEFIT APPROVAL CERTIFICATE

===============================================

Application ID: {current_app_id}
Issue Date: {datetime.now().strftime('%B %d, %Y')}

APPLICANT INFORMATION:
Name: {form_data.get('full_name', 'N/A')}
Emirates ID: {form_data.get('emirates_id', 'N/A')}
Email: {form_data.get('email', 'N/A')}

APPROVAL DETAILS:
Status: APPROVED
Benefit Amount: {currency} {benefit_amount:,.0f} per month
Effective Date: {effective_date}
Decision Confidence: {float(decision.get('confidence_score', 0)):.1%}

NEXT STEPS:
1. Visit your local social security office within 7 days
2. Bring original documents for verification
3. Set up direct deposit for benefit payments
4. Attend mandatory orientation session

For questions or support:
Phone: +971-4-123-4567
Email: support@socialsecurity.gov.ae

This certificate is valid for 30 days from the issue date.

===============================================
AI-Generated Certificate
Social Security AI System v1.0
"""
    return certificate


def print_results():
    """Show print instructions"""
    st.info("""
    **🖨️ To print these results:**

    1. Use your browser's print function (Ctrl+P or Cmd+P)
    2. Select "Print" destination
    3. Choose appropriate page settings
    4. Click "Print"

    For best results, use landscape orientation.
    """)


def show_chat_support():
    """Show chat support interface"""
    st.info("""
    **💬 Chat Support:**

    For immediate assistance, you can:

    1. **WhatsApp:** +971-50-123-4567
    2. **Live Chat:** Available on our website
    3. **Email:** support@socialsecurity.gov.ae

    **Support Hours:**
    Sunday - Thursday: 8:00 AM - 6:00 PM
    Friday - Saturday: Closed

    Average response time: 15 minutes
    """)


def start_new_application():
    """Start a new application"""
    # Confirm action
    if st.button("✅ Confirm: Start New Application", type="secondary"):
        reset_application_state()
        set_success_message("🆕 Ready for new application!")
        st.rerun()
    else:
        st.warning("⚠️ This will clear your current application data. Click 'Confirm' to proceed.")