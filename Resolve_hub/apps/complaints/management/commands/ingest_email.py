import email
import imaplib
import logging
from email.header import decode_header
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import Role
from apps.complaints.models import Complaint, SourceChannel
from apps.complaints.services import register_complaint
from apps.institutions.models import Institution

logger = logging.getLogger(__name__)


def _clean_header(header_val: str) -> str:
    if not header_val:
        return ""
    decoded_parts = decode_header(header_val)
    text = ""
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            text += part.decode(enc or "utf-8", errors="replace")
        else:
            text += str(part)
    return text.strip()


class Command(BaseCommand):
    help = "Poll configured IMAP mailbox for incoming grievance emails (idempotent via Message-ID)."

    def handle(self, *args, **options):
        imap_host = getattr(settings, "IMAP_HOST", "")
        imap_user = getattr(settings, "IMAP_USER", "")
        imap_password = getattr(settings, "IMAP_PASSWORD", "")
        imap_folder = getattr(settings, "IMAP_FOLDER", "INBOX")

        if not (imap_host and imap_user and imap_password):
            self.stdout.write(self.style.WARNING("Email intake disabled: IMAP_* settings not configured in .env."))
            return

        try:
            mail = imaplib.IMAP4_SSL(imap_host)
            mail.login(imap_user, imap_password)
            mail.select(imap_folder)

            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                self.stdout.write("No unread messages found.")
                return

            email_ids = messages[0].split()
            created = 0
            skipped = 0
            User = get_user_model()

            for e_id in email_ids:
                res, msg_data = mail.fetch(e_id, "(RFC822)")
                if res != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                msg_id = msg.get("Message-ID", f"email-{e_id.decode()}").strip()
                if Complaint.objects.filter(external_reference=msg_id).exists():
                    skipped += 1
                    continue

                subject = _clean_header(msg.get("Subject", "Email Grievance"))
                from_header = _clean_header(msg.get("From", ""))
                from_email = email.utils.parseaddr(from_header)[1].lower()

                # Extract body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="replace")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="replace")

                # Match or create user
                user = User.objects.filter(email=from_email).first()
                if not user:
                    user = User.objects.create_user(
                        username=from_email,
                        email=from_email,
                        full_name=from_header.split("<")[0].strip() or "Email Complainant",
                        role=Role.STUDENT,
                        is_active=True,
                    )

                # Attempt to find institution in subject or body
                text_to_search = f"{subject} {body}"
                institution = None
                for inst in Institution.objects.filter(is_active=True):
                    if inst.aicte_id in text_to_search or inst.name.lower() in text_to_search.lower():
                        institution = inst
                        break

                register_complaint(
                    submitting_user=user,
                    institution=institution,
                    subject=subject[:200],
                    description=body[:5000] if body else "No body text provided in email.",
                    source_channel=SourceChannel.EMAIL,
                    external_reference=msg_id,
                    consent_given=True,
                )
                created += 1

            mail.close()
            mail.logout()
            self.stdout.write(self.style.SUCCESS(f"Email intake complete: {created} processed, {skipped} skipped."))

        except Exception as exc:
            logger.error("IMAP error during ingest_email: %s", exc)
            self.stdout.write(self.style.ERROR(f"IMAP error: {exc}"))
