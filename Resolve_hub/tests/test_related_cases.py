from django.test import TestCase
from apps.complaints.models import Complaint, ComplaintCategory, ComplaintRelationship
from apps.institutions.models import Institution, Cell, Bureau
from apps.complaints.ai_service import find_related_complaints

class RelatedCasesTestCase(TestCase):
    def setUp(self):
        self.bureau = Bureau.objects.create(name="Approval Bureau", slug="ab")
        self.cell = Cell.objects.create(name="Public Grievance Cell", slug="pgc", bureau=self.bureau)
        self.category = ComplaintCategory.objects.create(name="Faculty", slug="faculty")

        # Institution 1
        self.inst1 = Institution.objects.create(
            name="Techno Engineering Institute",
            aicte_id="1-11223344",
            state="Karnataka",
            district="Bangalore",
        )
        # Institution 2 (different institution)
        self.inst2 = Institution.objects.create(
            name="National Science Academy",
            aicte_id="1-55667788",
            state="Tamil Nadu",
            district="Chennai",
        )

        # Complaint 1 on Institution 1
        self.c1 = Complaint.objects.create(
            complaint_code="CASE-INST1-01",
            category=self.category,
            institution=self.inst1,
            cell=self.cell,
            subject="Severe faculty shortage in Computer Science and Engineering Department",
            description="The Computer Science department lacks required qualified professors as mandated by AICTE guidelines. No professors for Artificial Intelligence lectures.",
            status="UNDER_REVIEW",
        )

        # Complaint 2 on Institution 1 (Similar text, same institution)
        self.c2 = Complaint.objects.create(
            complaint_code="CASE-INST1-02",
            category=self.category,
            institution=self.inst1,
            cell=self.cell,
            subject="Acute faculty shortage in CSE Department for Artificial Intelligence course",
            description="The CSE department has a shortage of qualified professors for AI subjects as required by AICTE regulations. Lectures cancelled repeatedly.",
            status="SUBMITTED",
        )

        # Complaint 3 on Institution 2 (Exact same text as Complaint 1, but DIFFERENT institution)
        self.c3 = Complaint.objects.create(
            complaint_code="CASE-INST2-03",
            category=self.category,
            institution=self.inst2,
            cell=self.cell,
            subject="Severe faculty shortage in Computer Science and Engineering Department",
            description="The Computer Science department lacks required qualified professors as mandated by AICTE guidelines. No professors for Artificial Intelligence lectures.",
            status="UNDER_REVIEW",
        )

    def test_strict_institutional_scoping(self):
        """
        Related complaints must NEVER link across different institutions.
        C1 and C2 (same institution) must link.
        C1 and C3 (different institution) must NEVER link despite identical subject/description.
        """
        find_related_complaints(self.c1)

        # Check links from C1
        c1_related = ComplaintRelationship.objects.filter(source_complaint=self.c1)
        linked_targets = [r.target_complaint.complaint_code for r in c1_related]

        self.assertIn("CASE-INST1-02", linked_targets, "C1 must be linked to C2 (same institution)")
        self.assertNotIn("CASE-INST2-03", linked_targets, "C1 must NEVER be linked to C3 (different institution)")

        # Verify all existing links in database are strictly within the same institution
        for rel in ComplaintRelationship.objects.all():
            self.assertEqual(
                rel.source_complaint.institution_id,
                rel.target_complaint.institution_id,
                "Relationship crosses institution boundaries! Strictly forbidden.",
            )

    def test_duplicate_similarity_score_and_type(self):
        """Verify similarity score is computed and relationship classified correctly."""
        find_related_complaints(self.c1)
        rel = ComplaintRelationship.objects.filter(
            source_complaint=self.c1, target_complaint=self.c2
        ).first()

        self.assertIsNotNone(rel)
        self.assertGreater(rel.similarity_score, 0.20, "Similar complaints should have > 20% similarity")
        self.assertIn(
            rel.relationship_type,
            [
                ComplaintRelationship.RelationshipType.POTENTIAL_DUPLICATE,
                ComplaintRelationship.RelationshipType.CONFIRMED_DUPLICATE,
                ComplaintRelationship.RelationshipType.SIMILAR_COMPLAINT,
                ComplaintRelationship.RelationshipType.SAME_TOPIC,
                ComplaintRelationship.RelationshipType.SAME_INSTITUTION,
            ],
        )

    def test_confirm_duplicate(self):
        """Test confirming a relationship updates is_confirmed."""
        find_related_complaints(self.c1)
        rel = ComplaintRelationship.objects.filter(
            source_complaint=self.c1, target_complaint=self.c2
        ).first()
        self.assertIsNotNone(rel)
        rel.is_confirmed = True
        rel.save()

        updated_rel = ComplaintRelationship.objects.get(pk=rel.pk)
        self.assertTrue(updated_rel.is_confirmed)
