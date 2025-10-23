import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


def send_verification_email(recipient_email: str, verification_code: str) -> bool:
    """
    Send verification code email using Gmail SMTP
    
    Args:
        recipient_email: The recipient's email address
        verification_code: The 5-digit verification code
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Email configuration - use environment variables for security
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = os.getenv("SMTP_EMAIL")  # Your Gmail address
    SENDER_PASSWORD = os.getenv("SMTP_PASSWORD")  # Your Gmail App Password
    
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        raise ValueError("SMTP_EMAIL and SMTP_PASSWORD environment variables must be set")
    
    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = "Password Reset Verification Code"
    message["From"] = SENDER_EMAIL
    message["To"] = recipient_email
    
    # Create the plain text version
    text = f"""
    Hello,
    
    Your password reset verification code is: {verification_code}
    
    This code will expire in 15 minutes.
    
    If you didn't request a password reset, please ignore this email.
    
    Best regards,
    Your App Team
    """
    
    # Create the HTML version
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
          <h2 style="color: #4CAF50;">Password Reset Request</h2>
          <p>Hello,</p>
          <p>You have requested to reset your password. Please use the verification code below:</p>
          <div style="background-color: #f4f4f4; padding: 20px; text-align: center; margin: 20px 0; border-radius: 5px;">
            <h1 style="color: #4CAF50; font-size: 32px; letter-spacing: 5px; margin: 0;">{verification_code}</h1>
          </div>
          <p style="color: #666; font-size: 14px;">This code will expire in <strong>15 minutes</strong>.</p>
          <p style="color: #999; font-size: 12px; margin-top: 30px;">
            If you didn't request a password reset, please ignore this email or contact support if you have concerns.
          </p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
          <p style="color: #999; font-size: 12px;">Best regards,<br>Your App Team</p>
        </div>
      </body>
    </html>
    """
    
    # Attach both plain text and HTML versions
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)
    
    try:
        # Create SMTP session
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Enable TLS encryption
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(message)
        
        print(f"Verification email sent successfully to {recipient_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("SMTP Authentication failed. Check your email and app password.")
        raise
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {str(e)}")
        raise
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        raise


def send_password_reset_confirmation(recipient_email: str, user_name: Optional[str] = None) -> bool:
    """
    Send confirmation email after successful password reset
    
    Args:
        recipient_email: The recipient's email address
        user_name: Optional user name for personalization
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = os.getenv("SMTP_EMAIL")
    SENDER_PASSWORD = os.getenv("SMTP_PASSWORD")
    
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        raise ValueError("SMTP_EMAIL and SMTP_PASSWORD environment variables must be set")
    
    greeting = f"Hello {user_name}," if user_name else "Hello,"
    
    message = MIMEMultipart("alternative")
    message["Subject"] = "Password Reset Successful"
    message["From"] = SENDER_EMAIL
    message["To"] = recipient_email
    
    text = f"""
    {greeting}
    
    Your password has been successfully reset.
    
    If you did not make this change, please contact our support team immediately.
    
    Best regards,
    Your App Team
    """
    
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
          <h2 style="color: #4CAF50;">Password Reset Successful</h2>
          <p>{greeting}</p>
          <p>Your password has been successfully reset.</p>
          <div style="background-color: #e8f5e9; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0;">
            <p style="margin: 0; color: #2e7d32;">✓ Your account is now secure with your new password.</p>
          </div>
          <p style="color: #d32f2f; font-size: 14px;">
            <strong>Important:</strong> If you did not make this change, please contact our support team immediately.
          </p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
          <p style="color: #999; font-size: 12px;">Best regards,<br>Your App Team</p>
        </div>
      </body>
    </html>
    """
    
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(message)
        
        print(f"Password reset confirmation sent to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"Failed to send confirmation email: {str(e)}")
        raise