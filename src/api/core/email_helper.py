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
        import traceback
        try:
            print(f"[SMTP DEBUG] Creating email message...")
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((self.from_name, self.from_email))

            # Parse and format email addresses
            to_formatted = self._format_email_addresses(to_email)
            to_emails = self._parse_email_addresses(to_email)
            msg['To'] = ', '.join([formataddr((name, email)) for name, email in to_formatted])
            print(f"[SMTP DEBUG] To: {msg['To']}")

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
            print(f"[SMTP DEBUG] Connecting to {self.smtp_host}:{self.smtp_port}...")
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                print(f"[SMTP DEBUG] Connected successfully")

                if self.smtp_use_tls:
                    print(f"[SMTP DEBUG] Starting TLS...")
                    server.starttls()
                    print(f"[SMTP DEBUG] TLS started")

                if self.smtp_username and self.smtp_password:
                    print(f"[SMTP DEBUG] Logging in as {self.smtp_username}...")
                    server.login(self.smtp_username, self.smtp_password)
                    print(f"[SMTP DEBUG] Login successful")
                else:
                    print(f"[SMTP ERROR] Missing SMTP credentials! Username: {self.smtp_username}, Password set: {bool(self.smtp_password)}")

                print(f"[SMTP DEBUG] Sending message to {to_emails}...")
                server.send_message(msg)
                print(f"[SMTP DEBUG] Message sent!")

            print(f"[SMTP SUCCESS] Email sent successfully to {', '.join(to_emails)}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"[SMTP ERROR] Authentication failed: {e}")
            print(f"[SMTP ERROR] Check your SMTP_USERNAME and SMTP_PASSWORD in .env")
            return False
        except smtplib.SMTPConnectError as e:
            print(f"[SMTP ERROR] Connection failed: {e}")
            print(f"[SMTP ERROR] Check your SMTP_HOST and SMTP_PORT in .env")
            return False
        except smtplib.SMTPException as e:
            print(f"[SMTP ERROR] SMTP error: {e}")
            print(f"[SMTP ERROR] Full traceback:\n{traceback.format_exc()}")
            return False
        except Exception as e:
            print(f"[SMTP ERROR] Unexpected error: {e}")
            print(f"[SMTP ERROR] Full traceback:\n{traceback.format_exc()}")
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
            import traceback
            print(f"[EMAIL DEBUG] Background thread started for email to: {to_email}")
            print(f"[EMAIL DEBUG] Template ID: {email_template_id}")
            print(f"[EMAIL DEBUG] Replacements: {replacements}")

            try:
                # Create session if not provided
                close_session = False
                if not session:
                    print("[EMAIL DEBUG] Creating new database session...")
                    from src.lib.db_con import engine  # Import database engine
                    local_session = Session(engine)
                    close_session = True
                    print("[EMAIL DEBUG] Database session created successfully")
                else:
                    local_session = session
                    print("[EMAIL DEBUG] Using provided session")

                # Get template from database
                print(f"[EMAIL DEBUG] Fetching template ID {email_template_id} from database...")
                template = self._get_template_from_db(local_session, email_template_id)

                if not template:
                    print(f"[EMAIL ERROR] Email template with ID {email_template_id} not found in database!")
                    if close_session:
                        local_session.close()
                    return

                print(f"[EMAIL DEBUG] Template found: {template.name}, is_active: {template.is_active}")

                if not template.is_active:
                    print(f"[EMAIL ERROR] Email template with ID {email_template_id} is not active!")
                    if close_session:
                        local_session.close()
                    return

                # Apply replacements to subject and content
                subject = self._apply_replacements(template.subject, replacements or {})
                print(f"[EMAIL DEBUG] Subject after replacements: {subject}")

                # Handle HTML content
                html_content = ""
                if template.html_content:
                    html_content = self._apply_replacements(template.html_content, replacements or {})
                    print(f"[EMAIL DEBUG] Using html_content (length: {len(html_content)})")
                elif template.content:
                    # If no HTML content, try to create from JSON content
                    content_data = template.content or {}
                    html_content = self._apply_replacements(str(content_data), replacements or {})
                    print(f"[EMAIL DEBUG] Using content field (length: {len(html_content)})")
                else:
                    print("[EMAIL ERROR] No html_content or content found in template!")

                # Debug SMTP config
                print(f"[EMAIL DEBUG] SMTP Host: {self.smtp_host}")
                print(f"[EMAIL DEBUG] SMTP Port: {self.smtp_port}")
                print(f"[EMAIL DEBUG] SMTP Username: {self.smtp_username}")
                print(f"[EMAIL DEBUG] SMTP Password: {'***' if self.smtp_password else 'NOT SET!'}")
                print(f"[EMAIL DEBUG] From Email: {self.from_email}")
                print(f"[EMAIL DEBUG] From Name: {self.from_name}")

                # Send email
                print(f"[EMAIL DEBUG] Calling _send_email_sync...")
                result = self._send_email_sync(
                    to_email=to_email,
                    subject=subject,
                    html_content=html_content,
                    cc=cc,
                    bcc=bcc
                )
                print(f"[EMAIL DEBUG] _send_email_sync returned: {result}")

                # Close session if we created it
                if close_session:
                    local_session.close()
                    print("[EMAIL DEBUG] Database session closed")

            except Exception as e:
                print(f"[EMAIL ERROR] Exception in background email sending: {e}")
                print(f"[EMAIL ERROR] Full traceback:\n{traceback.format_exc()}")
        
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