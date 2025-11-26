# src/api/routes/contactusRoute.py
from fastapi import APIRouter
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requirePermission,
)
from src.api.models.contactusModel import (
    ContactUs,
    ContactUsSupportCreate,
    ContactUsSendCreate,
    ContactUsRead,
    ContactUsUpdate
)

router = APIRouter(prefix="/contactus", tags=["ContactUs"])


def send_contact_email(name: str, email: str, subject: str, message: str, category: str = None) -> bool:
    """
    Send contact form submission email to support@ghertak.com

    Args:
        name: Sender's name
        email: Sender's email address
        subject: Email subject
        message: Message content
        category: Optional category (only for /support endpoint)

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Email configuration from environment variables
    SMTP_SERVER = os.getenv("SMTP_HOST", "mail.ghertak.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SENDER_EMAIL = os.getenv("SMTP_EMAIL", "support@ghertak.com")
    SENDER_PASSWORD = os.getenv("SMTP_PASSWORD")
    FROM_NAME = os.getenv("FROM_NAME", "Ghertak Contact Form")
    SUPPORT_EMAIL = "support@ghertak.com"

    if not SENDER_PASSWORD:
        raise ValueError("SMTP_PASSWORD environment variable must be set")

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Contact Form: {subject}"
    msg["From"] = f"{FROM_NAME} <{SENDER_EMAIL}>"
    msg["To"] = SUPPORT_EMAIL
    msg["Reply-To"] = email

    # Create the HTML version with modern design
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Contact Form Submission</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7fa;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f7fa; padding: 40px 0;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 600; letter-spacing: -0.5px;">
                                    New Contact Form Submission
                                </h1>
                            </td>
                        </tr>

                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 30px;">
                                <p style="margin: 0 0 30px 0; color: #718096; font-size: 16px; line-height: 24px;">
                                    You have received a new message from your website contact form.
                                </p>

                                <!-- Contact Information Table -->
                                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 30px;">
                                    <tr>
                                        <td style="padding: 20px; background-color: #f7fafc; border-radius: 8px;">
                                            <table width="100%" cellpadding="8" cellspacing="0" border="0">
                                                <tr>
                                                    <td width="140" style="color: #4a5568; font-weight: 600; font-size: 14px; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                                                        Name:
                                                    </td>
                                                    <td style="color: #2d3748; font-size: 14px; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                                                        {name}
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td style="color: #4a5568; font-weight: 600; font-size: 14px; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                                                        Email:
                                                    </td>
                                                    <td style="color: #2d3748; font-size: 14px; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                                                        <a href="mailto:{email}" style="color: #667eea; text-decoration: none;">{email}</a>
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td style="color: #4a5568; font-weight: 600; font-size: 14px; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                                                        Subject:
                                                    </td>
                                                    <td style="color: #2d3748; font-size: 14px; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                                                        {subject}
                                                    </td>
                                                </tr>
                                                {f'''<tr>
                                                    <td style="color: #4a5568; font-weight: 600; font-size: 14px; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                                                        Category:
                                                    </td>
                                                    <td style="color: #2d3748; font-size: 14px; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                                                        <span style="background-color: #667eea; color: #ffffff; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                                                            {category}
                                                        </span>
                                                    </td>
                                                </tr>''' if category else ''}
                                                <tr>
                                                    <td style="color: #4a5568; font-weight: 600; font-size: 14px; padding: 12px 0;">
                                                        Submitted:
                                                    </td>
                                                    <td style="color: #2d3748; font-size: 14px; padding: 12px 0;">
                                                        {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Message Section -->
                                <div style="margin-bottom: 30px;">
                                    <h3 style="margin: 0 0 15px 0; color: #2d3748; font-size: 18px; font-weight: 600;">
                                        Message:
                                    </h3>
                                    <div style="background-color: #f7fafc; border-left: 4px solid #667eea; padding: 20px; border-radius: 4px;">
                                        <p style="margin: 0; color: #4a5568; font-size: 15px; line-height: 26px; white-space: pre-wrap;">
{message}
                                        </p>
                                    </div>
                                </div>

                                <!-- Action Button -->
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td align="center" style="padding: 20px 0;">
                                            <a href="mailto:{email}?subject=Re: {subject}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 600; font-size: 14px; letter-spacing: 0.5px;">
                                                Reply to {name}
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f7fafc; padding: 30px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0 0 10px 0; color: #718096; font-size: 13px; line-height: 20px;">
                                    This is an automated message from your website contact form.
                                </p>
                                <p style="margin: 0; color: #a0aec0; font-size: 12px;">
                                    &copy; {datetime.now().year} Ghertak. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # Create plain text version
    text_content = f"""
    New Contact Form Submission

    Name: {name}
    Email: {email}
    Subject: {subject}
    {f'Category: {category}' if category else ''}
    Submitted: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

    Message:
    {message}

    ---
    Reply to: {email}
    """

    # Attach both versions
    part1 = MIMEText(text_content, "plain")
    part2 = MIMEText(html, "html")
    msg.attach(part1)
    msg.attach(part2)

    try:
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"Contact form email sent successfully to {SUPPORT_EMAIL}")
        return True

    except Exception as e:
        print(f"Failed to send contact form email: {str(e)}")
        raise


# ✅ CREATE Contact Submission - /contactus/support (with category)
@router.post("/support")
def create_support_contact(
    request: ContactUsSupportCreate,
    session: GetSession,
):
    """
    Submit a support contact form with category.
    Sends email to support@ghertak.com and stores in database.
    """
    print("📧 Creating support contact:", request.model_dump())

    try:
        # Save to database
        contact = ContactUs(**request.model_dump())
        session.add(contact)
        session.commit()
        session.refresh(contact)

        # Send email to support
        send_contact_email(
            name=request.name,
            email=request.email,
            subject=request.subject,
            message=request.message,
            category=request.category
        )

        return api_response(
            201,
            "Thank you for contacting us! We'll get back to you soon.",
            ContactUsRead.model_validate(contact)
        )

    except Exception as e:
        session.rollback()
        print(f"Error creating support contact: {str(e)}")
        return api_response(500, f"Failed to submit contact form: {str(e)}")


# ✅ CREATE Contact Submission - /contactus/send (without category)
@router.post("/send")
def create_send_contact(
    request: ContactUsSendCreate,
    session: GetSession,
):
    """
    Submit a general contact form without category.
    Sends email to support@ghertak.com and stores in database.
    """
    print("📧 Creating contact submission:", request.model_dump())

    try:
        # Save to database
        contact = ContactUs(**request.model_dump())
        session.add(contact)
        session.commit()
        session.refresh(contact)

        # Send email to support
        send_contact_email(
            name=request.name,
            email=request.email,
            subject=request.subject,
            message=request.message
        )

        return api_response(
            201,
            "Thank you for your message! We'll respond as soon as possible.",
            ContactUsRead.model_validate(contact)
        )

    except Exception as e:
        session.rollback()
        print(f"Error creating contact submission: {str(e)}")
        return api_response(500, f"Failed to submit contact form: {str(e)}")


# ✅ READ Contact by ID (Admin only)
@router.get("/read/{id}")
def read_contact(
    id: int,
    session: GetSession,
    user=requirePermission("contactus:view")
):
    """Get a specific contact submission by ID"""
    contact = session.get(ContactUs, id)
    raiseExceptions((contact, 404, "Contact submission not found"))

    return api_response(200, "Contact found", ContactUsRead.model_validate(contact))


# ✅ UPDATE Contact (Admin only - for marking as processed and adding notes)
@router.put("/update/{id}")
def update_contact(
    id: int,
    request: ContactUsUpdate,
    session: GetSession,
    user=requirePermission("contactus:update"),
):
    """Update contact submission status and notes (admin only)"""
    contact = session.get(ContactUs, id)
    raiseExceptions((contact, 404, "Contact submission not found"))

    updated = updateOp(contact, request, session)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Contact updated successfully", ContactUsRead.model_validate(updated))


# ✅ DELETE Contact (Admin only)
@router.delete("/delete/{id}")
def delete_contact(
    id: int,
    session: GetSession,
    user=requirePermission("contactus:delete"),
):
    """Delete a contact submission (admin only)"""
    contact = session.get(ContactUs, id)
    raiseExceptions((contact, 404, "Contact submission not found"))

    session.delete(contact)
    session.commit()
    return api_response(200, f"Contact submission deleted successfully")


# ✅ LIST ALL Contacts (Admin - with pagination and search)
@router.get("/list", response_model=list[ContactUsRead])
def list_contacts(
    query_params: ListQueryParams,
    user=requirePermission("contactus:view_all")
):
    """List all contact submissions with pagination and search (admin only)"""
    query_params = vars(query_params)
    searchFields = ["name", "email", "subject", "message", "category"]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=ContactUs,
        Schema=ContactUsRead,
    )


# ✅ GET Contact Count (Admin)
@router.get("/count")
def get_contact_count(
    session: GetSession,
    user=requirePermission("contactus:view_all")
):
    """Get count of all contacts, processed, and unprocessed"""
    from sqlalchemy import select

    total_contacts = session.exec(select(ContactUs)).all()
    processed_contacts = session.exec(select(ContactUs).where(ContactUs.is_processed == True)).all()

    return api_response(200, "Contact counts retrieved", {
        "total": len(total_contacts),
        "processed": len(processed_contacts),
        "unprocessed": len(total_contacts) - len(processed_contacts)
    })
