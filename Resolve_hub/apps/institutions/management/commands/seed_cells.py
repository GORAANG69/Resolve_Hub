from django.core.management.base import BaseCommand
from apps.institutions.models import Bureau, Cell


class Command(BaseCommand):
    help = "Seed standard AICTE Bureaus and Cells (idempotent)."

    def handle(self, *args, **options):
        bureaus_data = [
            {
                "name": "Approvals & Licensing Bureau",
                "slug": "approval-bureau",
                "cells": [
                    {"name": "Approval", "slug": "approval", "default_sla_hours": 120},
                    {"name": "Curriculum & Faculty Standards", "slug": "curriculum-faculty", "default_sla_hours": 168},
                ],
            },
            {
                "name": "Public Grievance & Student Welfare Bureau",
                "slug": "pgrc-bureau",
                "cells": [
                    {"name": "PGRC", "slug": "pgrc", "default_sla_hours": 72},
                    {"name": "Student Anti-Ragging & Safety", "slug": "anti-ragging", "default_sla_hours": 48},
                ],
            },
            {
                "name": "Regional Coordination & Field Offices",
                "slug": "regional-bureau",
                "cells": [
                    {"name": "Regional Office", "slug": "regional-office", "default_sla_hours": 96},
                ],
            },
            {
                "name": "Legal, RTI & Compliance Bureau",
                "slug": "legal-bureau",
                "cells": [
                    {"name": "Legal", "slug": "legal", "default_sla_hours": 48},
                    {"name": "RTI & Parliament Matters", "slug": "rti-parliament", "default_sla_hours": 48},
                ],
            },
        ]

        b_created_count = 0
        c_created_count = 0

        for b_data in bureaus_data:
            bureau, b_created = Bureau.objects.get_or_create(
                slug=b_data["slug"],
                defaults={"name": b_data["name"], "is_active": True},
            )
            if b_created:
                b_created_count += 1

            for c_data in b_data["cells"]:
                cell, c_created = Cell.objects.get_or_create(
                    slug=c_data["slug"],
                    defaults={
                        "bureau": bureau,
                        "name": c_data["name"],
                        "default_sla_hours": c_data["default_sla_hours"],
                        "is_active": True,
                    },
                )
                if c_created:
                    c_created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Bureaus and Cells seeded: {b_created_count} bureaus created, {c_created_count} cells created."
            )
        )
