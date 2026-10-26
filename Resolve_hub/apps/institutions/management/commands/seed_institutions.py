from django.core.management.base import BaseCommand
from apps.institutions.models import Institution, InstitutionType


class Command(BaseCommand):
    help = "Seed ~15 realistic AICTE institutions across multiple states (idempotent)."

    def handle(self, *args, **options):
        sample_institutions = [
            {
                "aicte_id": "1-10023451",
                "name": "Delhi Institute of Technology & Management",
                "state": "Delhi",
                "district": "New Delhi",
                "institution_type": InstitutionType.ENGINEERING,
            },
            {
                "aicte_id": "1-20045612",
                "name": "Maharashtra Institute of Technology",
                "state": "Maharashtra",
                "district": "Pune",
                "institution_type": InstitutionType.ENGINEERING,
            },
            {
                "aicte_id": "1-30067823",
                "name": "Karnataka College of Pharmacy",
                "state": "Karnataka",
                "district": "Bengaluru Urban",
                "institution_type": InstitutionType.PHARMACY,
            },
            {
                "aicte_id": "1-40089134",
                "name": "Tamil Nadu School of Architecture & Design",
                "state": "Tamil Nadu",
                "district": "Chennai",
                "institution_type": InstitutionType.ARCHITECTURE,
            },
            {
                "aicte_id": "1-50112345",
                "name": "Gujarat Technological Polytechnic Institute",
                "state": "Gujarat",
                "district": "Ahmedabad",
                "institution_type": InstitutionType.POLYTECHNIC,
            },
            {
                "aicte_id": "1-60134567",
                "name": "National School of Business & Management Studies",
                "state": "Uttar Pradesh",
                "district": "Noida",
                "institution_type": InstitutionType.MANAGEMENT,
            },
            {
                "aicte_id": "1-70156789",
                "name": "Rajasthan Institute of Engineering & Technology",
                "state": "Rajasthan",
                "district": "Jaipur",
                "institution_type": InstitutionType.ENGINEERING,
            },
            {
                "aicte_id": "1-80178901",
                "name": "Madhya Pradesh College of Pharmaceutical Sciences",
                "state": "Madhya Pradesh",
                "district": "Bhopal",
                "institution_type": InstitutionType.PHARMACY,
            },
            {
                "aicte_id": "1-90201234",
                "name": "West Bengal Institute of Technology",
                "state": "West Bengal",
                "district": "Kolkata",
                "institution_type": InstitutionType.ENGINEERING,
            },
            {
                "aicte_id": "1-10223456",
                "name": "Telangana Advanced Polytechnic College",
                "state": "Telangana",
                "district": "Hyderabad",
                "institution_type": InstitutionType.POLYTECHNIC,
            },
            {
                "aicte_id": "1-11245678",
                "name": "Kerala Institute of Management & Governance",
                "state": "Kerala",
                "district": "Thiruvananthapuram",
                "institution_type": InstitutionType.MANAGEMENT,
            },
            {
                "aicte_id": "1-12267890",
                "name": "Punjab Technical & Engineering College",
                "state": "Punjab",
                "district": "Ludhiana",
                "institution_type": InstitutionType.ENGINEERING,
            },
            {
                "aicte_id": "1-13289012",
                "name": "Haryana Academy of Architectural Studies",
                "state": "Haryana",
                "district": "Gurugram",
                "institution_type": InstitutionType.ARCHITECTURE,
            },
            {
                "aicte_id": "1-14301234",
                "name": "Odisha College of Engineering & Research",
                "state": "Odisha",
                "district": "Bhubaneswar",
                "institution_type": InstitutionType.ENGINEERING,
            },
            {
                "aicte_id": "1-15323456",
                "name": "Assam State Technical Polytechnic",
                "state": "Assam",
                "district": "Guwahati",
                "institution_type": InstitutionType.POLYTECHNIC,
            },
            {
                "aicte_id": "1-16345678",
                "name": "Bihar Institute of Management Studies",
                "state": "Bihar",
                "district": "Patna",
                "institution_type": InstitutionType.MANAGEMENT,
            },
        ]

        created_count = 0
        for inst_data in sample_institutions:
            _, created = Institution.objects.get_or_create(
                aicte_id=inst_data["aicte_id"],
                defaults={
                    "name": inst_data["name"],
                    "state": inst_data["state"],
                    "district": inst_data["district"],
                    "institution_type": inst_data["institution_type"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Sample institutions seeded: {created_count} created, {len(sample_institutions) - created_count} already existed."
            )
        )
