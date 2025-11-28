# email_helper.py
import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import List, Optional, Union, Dict, Any
from dotenv import load_dotenv
from sqlmodel import Session, select
from src.api.models.email_model.emailModel import Emailtemplate

# Load environment variables
load_dotenv()

class EmailHelper:
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.from_name = os.getenv('FROM_NAME', 'System')
        
    def _get_template_from_db(self, session: Session, email_template_id: int) -> Optional[Emailtemplate]:
        """Retrieve email template from database"""
        try:
            statement = select(Emailtemplate).where(Emailtemplate.id == email_template_id)
            result = session.exec(statement)
            return result.first()
        except Exception as e:
            print(f"Error fetching email template: {e}")
            return None
    
    def _apply_replacements(self, text: str, replacements: Dict[str, Any]) -> str:
        """Apply replacements to text using {{key}} format"""
        if not text or not replacements:
            return text
            
        for key, value in replacements.items():
            placeholder = f"{{{{{key}}}}}"
            text = text.replace(placeholder, str(value))
        return text
    
    def _parse_email_addresses(self, emails: Union[str, List[str], List[Dict[str, str]]]) -> List[str]:
        """
        Parse email addresses from string, list, or list of dicts

        Accepts:
        - String: "email@example.com" or "email1@example.com, email2@example.com"
        - List of strings: ["email1@example.com", "email2@example.com"]
        - List of dicts: [{"name": "John Doe", "email": "john@example.com"}]
        """
        if isinstance(emails, str):
            # Split by common delimiters and clean up
            emails = [email.strip() for email in emails.replace(';', ',').split(',') if email.strip()]
        elif isinstance(emails, list) and emails and isinstance(emails[0], dict):
            # Extract email addresses from dict format
            emails = [item.get('email', '') for item in emails if item.get('email')]
        return emails

    def _format_email_addresses(self, emails: Union[str, List[str], List[Dict[str, str]]]) -> List[tuple]:
        """
        Format email addresses with names for display

        Returns list of tuples: [(name, email), ...]
        If no name provided, returns (email, email)
        """
        if isinstance(emails, str):
            # Simple string format - no names
            parsed = [email.strip() for email in emails.replace(';', ',').split(',') if email.strip()]
            return [(email, email) for email in parsed]
        elif isinstance(emails, list):
            if emails and isinstance(emails[0], dict):
                # Dict format with names
                return [(item.get('name', item.get('email', '')), item.get('email', ''))
                        for item in emails if item.get('email')]
            else:
                # List of strings - no names
                return [(email, email) for email in emails]
        return []
    
    def _send_email_sync(self, to_email: Union[str, List[str], List[Dict[str, str]]],
                        subject: str,
                        html_content: str,
                        plain_text_content: str = None,
                        cc: Optional[Union[str, List[str], List[Dict[str, str]]]] = None,
                        bcc: Optional[Union[str, List[str], List[Dict[str, str]]]] = None) -> bool:
        """
        Synchronous email sending function

        Args:
            to_email: Recipient(s) - string, list of strings, or list of dicts with name/email
            subject: Email subject
            html_content: HTML content
            plain_text_content: Plain text content (optional)
            cc: CC recipient(s) - string, list of strings, or list of dicts with name/email
            bcc: BCC recipient(s) - string, list of strings, or list of dicts with name/email
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((self.from_name, self.from_email))

            # Parse and format email addresses
            to_formatted = self._format_email_addresses(to_email)
            to_emails = self._parse_email_addresses(to_email)
            msg['To'] = ', '.join([formataddr((name, email)) for name, email in to_formatted])

            if cc:
                cc_formatted = self._format_email_addresses(cc)
                cc_emails = self._parse_email_addresses(cc)
                msg['CC'] = ', '.join([formataddr((name, email)) for name, email in cc_formatted])
                to_emails.extend(cc_emails)

            if bcc:
                # BCC emails are added to recipients but NOT to message headers
                bcc_emails = self._parse_email_addresses(bcc)
                to_emails.extend(bcc_emails)
            
            # Create plain text version if not provided
            if not plain_text_content:
                # Simple HTML to text conversion
                import re
                plain_text_content = re.sub('<[^<]+?>', '', html_content)
            
            # Attach both plain text and HTML versions
            part1 = MIMEText(plain_text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(msg)
            
            print(f"Email sent successfully to {', '.join(to_emails)}")
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def send_email(self,
                   to_email: Union[str, List[str], List[Dict[str, str]]],
                   email_template_id: int,
                   replacements: Optional[Dict[str, Any]] = None,
                   cc: Optional[Union[str, List[str], List[Dict[str, str]]]] = None,
                   bcc: Optional[Union[str, List[str], List[Dict[str, str]]]] = None,
                   session: Optional[Session] = None) -> None:
        """
        Send email using template in background

        Args:
            to_email: Recipient email(s) - string, list of strings, or list of dicts with name/email
            email_template_id: ID of the email template from database
            replacements: Dictionary of replacements for template tags
            cc: CC email(s) - string, list of strings, or list of dicts with name/email
            bcc: BCC email(s) - string, list of strings, or list of dicts with name/email
                  Format: [{"name": "John Doe", "email": "john@example.com"}]
            session: SQLModel session (will create if not provided)
        """
        
        def send_in_background():
            """Send email in background thread"""
            try:
                # Create session if not provided
                close_session = False
                if not session:
                    from src.lib.db_con import engine  # Import database engine
                    local_session = Session(engine)
                    close_session = True
                else:
                    local_session = session
                
                # Get template from database
                template = self._get_template_from_db(local_session, email_template_id)
                
                if not template:
                    print(f"Email template with ID {email_template_id} not found")
                    return
                
                if not template.is_active:
                    print(f"Email template with ID {email_template_id} is not active")
                    return
                
                # Apply replacements to subject and content
                subject = self._apply_replacements(template.subject, replacements or {})
                
                # Handle HTML content
                html_content = ""
                if template.html_content:
                    html_content = self._apply_replacements(template.html_content, replacements or {})
                elif template.content:
                    # If no HTML content, try to create from JSON content
                    content_data = template.content or {}
                    html_content = self._apply_replacements(str(content_data), replacements or {})
                
                # Send email
                self._send_email_sync(
                    to_email=to_email,
                    subject=subject,
                    html_content=html_content,
                    cc=cc,
                    bcc=bcc
                )
                
                # Close session if we created it
                if close_session:
                    local_session.close()
                    
            except Exception as e:
                print(f"Error in background email sending: {e}")
        
        # Start background thread
        thread = threading.Thread(target=send_in_background)
        thread.daemon = True
        thread.start()

# Create global instance
email_helper = EmailHelper()

# Convenience function
def send_email(to_email: Union[str, List[str], List[Dict[str, str]]],
               email_template_id: int,
               replacements: Optional[Dict[str, Any]] = None,
               cc: Optional[Union[str, List[str], List[Dict[str, str]]]] = None,
               bcc: Optional[Union[str, List[str], List[Dict[str, str]]]] = None,
               session: Optional[Session] = None) -> None:
    """
    Convenience function to send email in background

    Example usage:
        # Simple BCC (email only)
        send_email(
            to_email="user@example.com",
            email_template_id=1,
            replacements={"name": "John", "verification_link": "https://example.com/verify"},
            cc="manager@example.com",
            bcc=["admin@example.com", "log@example.com"]
        )

        # BCC with names and emails
        send_email(
            to_email="user@example.com",
            email_template_id=1,
            bcc=[
                {"name": "Admin User", "email": "admin@example.com"},
                {"name": "Log System", "email": "logs@example.com"}
            ]
        )

        # Mixed formats
        send_email(
            to_email=[{"name": "John Doe", "email": "john@example.com"}],
            email_template_id=1,
            cc="manager@example.com",
            bcc=[
                {"name": "Admin", "email": "admin@example.com"},
                {"name": "Support", "email": "support@example.com"}
            ]
        )
    """
    email_helper.send_email(
        to_email=to_email,
        email_template_id=email_template_id,
        replacements=replacements,
        cc=cc,
        bcc=bcc,
        session=session
    )