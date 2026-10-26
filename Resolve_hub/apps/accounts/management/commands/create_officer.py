from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from apps.accounts.models import Role
from apps.institutions.models import Bureau, Cell


class Command(BaseCommand):
    """
    Provision an AICTE Officer account administratively:
    SECTION_HEAD, BUREAU_HEAD, MEMBER_SECRETARY, or DIRECTOR.
    """

    help = "Create an AICTE Officer account (administrative provisioning only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--role",
            required=True,
            choices=[
                Role.SECTION_HEAD,
                Role.BUREAU_HEAD,
                Role.MEMBER_SECRETARY,
                Role.DIRECTOR,
            ],
            help="Officer role",
        )
        parser.add_argument("--email", required=True, help="Email address")
        parser.add_argument("--full-name", required=False, default="", help="Full Name")
        parser.add_argument("--password", required=True, help="Account password")
        parser.add_argument("--cell", required=False, help="Cell slug (for SECTION_HEAD)")
        parser.add_argument("--bureau", required=False, help="Bureau slug (for BUREAU_HEAD)")

    def handle(self, *args, **options):
        User = get_user_model()
        email = options["email"].strip().lower()
        role = options["role"]
        cell_slug = options.get("cell")
        bureau_slug = options.get("bureau")

        if User.objects.filter(email=email).exists():
            raise CommandError(f"A user with email {email} already exists.")

        cell = None
        bureau = None

        if role == Role.SECTION_HEAD:
            if not cell_slug:
                raise CommandError("--cell slug is required for role SECTION_HEAD.")
            try:
                cell = Cell.objects.get(slug=cell_slug)
                bureau = cell.bureau
            except Cell.DoesNotExist:
                raise CommandError(f"Cell with slug '{cell_slug}' does not exist.")

        elif role == Role.BUREAU_HEAD:
            if not bureau_slug:
                raise CommandError("--bureau slug is required for role BUREAU_HEAD.")
            try:
                bureau = Bureau.objects.get(slug=bureau_slug)
            except Bureau.DoesNotExist:
                raise CommandError(f"Bureau with slug '{bureau_slug}' does not exist.")

        full_name = options.get("full_name") or email.split("@")[0].title()

        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                full_name=full_name,
                password=options["password"],
                role=role,
                cell=cell,
                bureau=bureau,
                is_staff=False,
            )
        except IntegrityError as exc:
            raise CommandError(str(exc))

        self.stdout.write(
            self.style.SUCCESS(
                f"Officer account created: {user.email} (Role: {user.role}, Bureau: {user.bureau}, Cell: {user.cell})"
            )
        )
