import unittest

from app.governance.request_workflow import activation_status, validate_transition


class WorkflowTests(unittest.TestCase):
    def test_cannot_skip_security(self):
        with self.assertRaises(ValueError):
            validate_transition("submitted", "enabled", {})

    def test_workspace_agent_defaults_disabled(self):
        self.assertEqual(activation_status({"workspace_agent": True}), "disabled")

    def test_enable_requires_explicit_review(self):
        with self.assertRaises(ValueError):
            validate_transition("approved", "enabled", {"workspace_agent": True})

    def test_approved_review_can_enable(self):
        record = {
            "risk_review": {
                "reviewer": "security@example.test",
                "reviewed_at": "2026-10-15",
                "data_access_scope": "Read-only curated knowledge",
                "publishing_identity": "shared_connection",
                "external_write_actions": False,
            },
            "data_owner_approval": "APPROVAL-001",
        }
        validate_transition("approved", "enabled", record)