from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi import BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, List
import logging
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Ensure .env file has:
# MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_PORT, MAIL_SERVER
# MAIL_STARTTLS (True/False), MAIL_SSL_TLS (True/False)

# Resolve the template folder relative to this file's parent directory
TEMPLATE_FOLDER = Path("./templates")

if not TEMPLATE_FOLDER.exists():
    logger.error(f"Email template folder not found at: {TEMPLATE_FOLDER}")
    # You might want to raise an exception here if emails are critical

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_FROM_NAME="Jargon (SDE Platform)",
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True").lower() == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False").lower() == "true",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=TEMPLATE_FOLDER
)

fm = FastMail(conf)

class EmailService:
    """
    Service to send all application emails asynchronously via background tasks.
    All methods are static and designed to be called from the API layer.
    """

    @staticmethod
    async def _send_email_async(
        subject: str,
        email_to: EmailStr,
        template_body: Dict[str, Any],
        template_name: str
    ):
        """
        Internal helper to construct and send an email message.
        """
        message = MessageSchema(
            subject=f"Jargon (SDE) | {subject}",
            recipients=[email_to],
            template_body=template_body,
            subtype=MessageType.html
        )

        try:
            await fm.send_message(message, template_name=template_name)
            logger.info(f"Email sent to {email_to} with template {template_name}")
        except Exception as e:
            logger.error(f"Failed to send email to {email_to}: {e}")
            # In production, this error should be sent to a monitoring service

    @staticmethod
    def _add_task(
        background_tasks: BackgroundTasks,
        subject: str,
        email_to: EmailStr,
        template_body: Dict[str, Any],
        template_name: str
    ):
        """Adds the email sending function to the background task queue."""
        background_tasks.add_task(
            EmailService._send_email_async,
            subject,
            email_to,
            template_body,
            template_name
        )

    # --- USER ACCOUNT EMAILS ---

    @staticmethod
    def send_user_welcome_email(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        name: str
    ):
        """1. (User) Sent on initial user registration."""
        EmailService._add_task(
            background_tasks,
            "Welcome to Jargon!",
            email_to,
            {"title": "Welcome to Jargon!", "name": name},
            "user_welcome.html"
        )

    @staticmethod
    def send_email_verification(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        name: str,
        verification_link: str
    ):
        """2. (User) Sent to verify a new user's email address."""
        EmailService._add_task(
            background_tasks,
            "Verify Your Email Address",
            email_to,
            {"title": "Verify Your Email", "user_name": name, "verification_link": verification_link},
            "email_verification.html"
        )
    @staticmethod
    def send_email_verified_notice(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        name: str
    ):
        """3. (User) [NEW] Sent *after* a user successfully clicks the verification link."""
        EmailService._add_task(
            background_tasks,
            "Email Verified Successfully!",
            email_to,
            {"title": "Email Verified", "user_name": name},
            "email_verified_notice.html"
        )

    @staticmethod
    def send_password_reset_email(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        name: str,
        reset_link: str
    ):
        """3. (User/Org) Sent when a password reset is requested."""
        EmailService._add_task(
            background_tasks,
            "Reset Your Password",
            email_to,
            {"title": "Reset Your Password", "user_name": name, "reset_link": reset_link},
            "password_reset.html"
        )

    @staticmethod
    def send_password_change_notice(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        name: str
    ):
        """4. (User/Org) Security notice sent *after* a password has been changed."""
        EmailService._add_task(
            background_tasks,
            "Security Alert: Your Password Was Changed",
            email_to,
            {"title": "Password Changed", "user_name": name},
            "password_change_notice.html"
        )

    @staticmethod
    def send_email_change_notice(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        name: str,
        old_email: str
    ):
        """5. (User/Org) Security notice sent to the *old* email address."""
        EmailService._add_task(
            background_tasks,
            "Security Alert: Your Jargon Email Was Changed",
            email_to,
            {"title": "Email Changed", "user_name": name, "new_email": email_to, "old_email": old_email},
            "email_change_notice.html"
        )

    # --- ORGANIZATION LIFECYCLE EMAILS ---

    @staticmethod
    def send_org_welcome_email(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        org_name: str,
        public_org_id: str,
        api_key: str
    ):
        """6. (Org) Sent on initial org registration. Includes API key and "Pending" status."""
        EmailService._add_task(
            background_tasks,
            "Welcome to Jargon! Your API Key is Ready.",
            email_to,
            {"title": "Welcome to Jargon!", "org_name": org_name, "public_org_id": public_org_id, "api_key": api_key},
            "org_approval_with_key.html"
        )

    @staticmethod
    def send_org_is_now_approved_email(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        org_name: str
    ):
        """7. (Org) Sent by an Admin to notify an org their API key is now active."""
        EmailService._add_task(
            background_tasks,
            "Your Jargon (SDE) Organization has been Approved",
            email_to,
            {"title": "You're Approved!", "org_name": org_name},
            "org_is_now_approved.html"
        )

    @staticmethod
    def send_account_suspended_email(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        name: str,
        reason: str
    ):
        """8. (User/Org) Security notice that an account has been suspended."""
        EmailService._add_task(
            background_tasks,
            "Important: Your Jargon Account Has Been Suspended",
            email_to,
            {"title": "Account Suspended", "user_name": name, "reason": reason},
            "account_suspended.html"
        )

    # --- CONSENT FLOW EMAILS ---

    @staticmethod
    def send_new_consent_request_email(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        user_name: str,
        org_name: str,
        plain_language_purpose: str
    ):
        """9. (User) Notifies user of a new, pending data request. Uses AI output."""
        EmailService._add_task(
            background_tasks,
            "Action Required: New Data Access Request",
            email_to,
            {"title": "New Data Request", "user_name": user_name, "org_name": org_name, "plain_language_purpose": plain_language_purpose},
            "new_consent_request.html"
        )

    @staticmethod
    def send_org_consent_approved_email(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        org_name: str,
        user_did: str,
        consent_id: str
    ):
        """10. (Org) Notifies an org that a user has approved their request."""
        EmailService._add_task(
            background_tasks,
            "A User Has Approved Your Data Request",
            email_to,
            {"title": "Consent Approved", "org_name": org_name, "user_did": user_did, "consent_id": consent_id},
            "org_consent_approved.html"
        )

    @staticmethod
    def send_org_consent_revoked_email(
        background_tasks: BackgroundTasks,
        email_to: EmailStr,
        org_name: str,
        user_did: str,
        consent_id: str
    ):
        """11. (Org) Notifies an org that a user has revoked access."""
        EmailService._add_task(
            background_tasks,
            "A User Has Revoked Data Consent",
            email_to,
            {"title": "Consent Revoked", "org_name": org_name, "user_did": user_did, "consent_id": consent_id},
            "org_consent_revoked.html"
        )
