# backend/Services/HelpdeskService/resources/emailService.py
import abc
import email.mime.multipart
import email.mime.text
import logging
import os
import smtplib
from typing import List, Optional

logger = logging.getLogger("helpdesk.emailService")


class EmailProvider(abc.ABC):
    """Abstract Email Provider for institutional dispatches."""

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Returns True only if an authentic email provider is configured."""
        pass

    @abc.abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> bool:
        """Dispatches an email. Returns True on verified delivery, False on failure or unconfigured."""
        pass


class SmtpEmailProvider(EmailProvider):
    """Standard SMTP email provider with TLS support."""

    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "").strip()
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USERNAME", "").strip()
        self.password = os.getenv("SMTP_PASSWORD", "").strip()
        self.from_email = os.getenv("SMTP_FROM_EMAIL", "helpdesk@college.edu").strip()
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    def is_configured(self) -> bool:
        # Must have host configured
        return bool(self.host)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> bool:
        if not self.is_configured():
            logger.warning("SMTP email delivery skipped: SMTP_HOST is not configured.")
            return False

        try:
            msg = email.mime.multipart.MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            part1 = email.mime.text.MIMEText(text_content, "plain")
            part2 = email.mime.text.MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_email, [to_email], msg.as_string())

            logger.info("Email successfully dispatched via SMTP to %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed to deliver email to %s via SMTP: %s", to_email, str(e))
            return False


class UnconfiguredEmailProvider(EmailProvider):
    """Default provider when no external email server is configured.
    Strictly follows: Do not simulate successful delivery when not configured.
    """

    def is_configured(self) -> bool:
        return False

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> bool:
        logger.warning(
            "Email notification skipped for %s ('%s'): No email provider configured.",
            to_email,
            subject,
        )
        # Explicitly return False — do NOT simulate successful delivery
        return False


class MockTestEmailProvider(EmailProvider):
    """Test provider used during automated testing to capture sent emails in memory."""

    def __init__(self):
        self.sent_emails: List[dict] = []
        self._enabled = True

    def is_configured(self) -> bool:
        return self._enabled

    def set_configured(self, configured: bool):
        self._enabled = configured

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> bool:
        if not self._enabled:
            return False
        self.sent_emails.append({
            "to_email": to_email,
            "subject": subject,
            "html_content": html_content,
            "text_content": text_content,
        })
        return True

    def clear(self):
        self.sent_emails.clear()


class EmailService:
    """Institutional Help Desk Email Notification Service."""

    def __init__(self):
        # Select provider based on environment
        smtp_host = os.getenv("SMTP_HOST", "").strip()
        if smtp_host:
            self.provider: EmailProvider = SmtpEmailProvider()
        else:
            self.provider: EmailProvider = UnconfiguredEmailProvider()

    def set_provider(self, provider: EmailProvider):
        """Allows test suites to plug in MockTestEmailProvider."""
        self.provider = provider

    def is_configured(self) -> bool:
        return self.provider.is_configured()

    async def notify_ticket_created(
        self,
        ticket_number: str,
        student_name: str,
        student_email: str,
        category: str,
        subject: str,
    ) -> bool:
        subject_line = f"Support Ticket Created: [{ticket_number}] {subject}"
        text_body = f"""Dear {student_name},

Your support request has been received by the College Help Desk.

Ticket ID: {ticket_number}
Category: {category}
Subject: {subject}
Status: OPEN

You can track your ticket anytime by visiting the Student Portal:
/tickets/{ticket_number}

Sincerely,
College AI Help Desk Administration
"""
        html_body = f"""<div style="font-family: sans-serif; max-width: 600px; padding: 20px; border: 1px solid #e2e8f0; rounded: 12px;">
<h2 style="color: #1e3a8a;">College Help Desk Ticket Confirmation</h2>
<p>Dear <strong>{student_name}</strong>,</p>
<p>Your support ticket has been registered with the College Help Desk administration.</p>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr><td style="padding: 6px 0; color: #64748b;">Ticket ID:</td><td><strong>{ticket_number}</strong></td></tr>
  <tr><td style="padding: 6px 0; color: #64748b;">Category:</td><td>{category}</td></tr>
  <tr><td style="padding: 6px 0; color: #64748b;">Subject:</td><td>{subject}</td></tr>
  <tr><td style="padding: 6px 0; color: #64748b;">Status:</td><td><span style="background: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 4px; font-weight: bold;">OPEN</span></td></tr>
</table>
<p style="margin-top: 20px;">Track your ticket at: <code>/tickets/{ticket_number}</code></p>
</div>"""
        return await self.provider.send_email(student_email, subject_line, html_body, text_body)

    async def notify_status_changed(
        self,
        ticket_number: str,
        student_name: str,
        student_email: str,
        old_status: str,
        new_status: str,
        reason: Optional[str] = None,
    ) -> bool:
        subject_line = f"Ticket Status Update: [{ticket_number}] is now {new_status}"
        text_body = f"""Dear {student_name},

The status of your ticket [{ticket_number}] has changed from {old_status} to {new_status}.

{f'Note: {reason}' if reason else ''}

Track your ticket: /tickets/{ticket_number}

College AI Help Desk
"""
        html_body = f"""<div style="font-family: sans-serif; max-width: 600px; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
<h3 style="color: #1e3a8a;">Ticket Status Update</h3>
<p>Dear <strong>{student_name}</strong>,</p>
<p>Your ticket <strong>{ticket_number}</strong> status changed to: <strong>{new_status}</strong></p>
{f'<p style="color: #475569; font-style: italic;">{reason}</p>' if reason else ''}
<p>Track your ticket: <code>/tickets/{ticket_number}</code></p>
</div>"""
        return await self.provider.send_email(student_email, subject_line, html_body, text_body)

    async def notify_staff_replied(
        self,
        ticket_number: str,
        student_name: str,
        student_email: str,
        staff_name: str,
        message_text: str,
    ) -> bool:
        subject_line = f"New Response on Ticket [{ticket_number}]"
        text_body = f"""Dear {student_name},

A staff member ({staff_name}) has responded to your ticket [{ticket_number}]:

"{message_text}"

Track and reply: /tickets/{ticket_number}

College AI Help Desk
"""
        html_body = f"""<div style="font-family: sans-serif; max-width: 600px; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
<h3 style="color: #1e3a8a;">New Response from Staff</h3>
<p>Dear <strong>{student_name}</strong>,</p>
<p><strong>{staff_name}</strong> has responded to your ticket <strong>{ticket_number}</strong>:</p>
<div style="background: #f8fafc; padding: 12px; border-left: 4px solid #2563eb; margin: 15px 0;">{message_text}</div>
<p>Reply via portal: <code>/tickets/{ticket_number}</code></p>
</div>"""
        return await self.provider.send_email(student_email, subject_line, html_body, text_body)

    async def notify_ticket_resolved(
        self,
        ticket_number: str,
        student_name: str,
        student_email: str,
        resolution_notes: str,
    ) -> bool:
        subject_line = f"Ticket Resolved: [{ticket_number}]"
        text_body = f"""Dear {student_name},

Your support ticket [{ticket_number}] has been marked as RESOLVED.

Resolution details:
{resolution_notes}

If your issue is not resolved, you may reply to reopen the ticket.

College AI Help Desk
"""
        html_body = f"""<div style="font-family: sans-serif; max-width: 600px; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
<h2 style="color: #059669;">Ticket Resolved</h2>
<p>Dear <strong>{student_name}</strong>,</p>
<p>Your support ticket <strong>{ticket_number}</strong> has been resolved.</p>
<div style="background: #ecfdf5; border: 1px solid #a7f3d0; padding: 12px; border-radius: 8px; margin: 15px 0;">
<strong>Resolution Information:</strong>
<p style="margin: 5px 0 0 0;">{resolution_notes}</p>
</div>
<p>View resolution: <code>/tickets/{ticket_number}</code></p>
</div>"""
        return await self.provider.send_email(student_email, subject_line, html_body, text_body)

    async def send_otp_email(
        self,
        to_email: str,
        ticket_number: str,
        otp_code: str,
        expires_minutes: int = 15,
    ) -> bool:
        subject_line = f"Verification Code for Ticket {ticket_number}: {otp_code}"
        text_body = f"""Your verification code to access ticket {ticket_number} is:

{otp_code}

This code expires in {expires_minutes} minutes.
Do not share this code with anyone.

College AI Help Desk
"""
        html_body = f"""<div style="font-family: sans-serif; max-width: 500px; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
<h3 style="color: #1e3a8a;">Ticket Access Verification</h3>
<p>You requested access to support ticket <strong>{ticket_number}</strong>.</p>
<div style="text-align: center; margin: 20px 0;">
  <span style="font-family: monospace; font-size: 32px; font-weight: bold; letter-spacing: 6px; background: #f1f5f9; padding: 8px 18px; border-radius: 8px; border: 1px solid #cbd5e1; color: #0f172a;">{otp_code}</span>
</div>
<p style="color: #64748b; font-size: 13px;">This code will expire in <strong>{expires_minutes} minutes</strong>. If you did not request this, please disregard.</p>
</div>"""
        return await self.provider.send_email(to_email, subject_line, html_body, text_body)


# Singleton instance
email_service = EmailService()
