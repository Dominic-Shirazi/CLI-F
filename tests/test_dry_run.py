import os
import unittest
from unittest.mock import patch

from system.graph import create_graph
from system.state import AgentState

class MockCLIResult:
    def __init__(self, stdout):
        self.stdout = stdout

class TestDryRunRouting(unittest.TestCase):
    def setUp(self):
        self.app = create_graph()
        self.config = {"configurable": {"thread_id": "test_thread"}}
        
        # Ensure only safe isolated directories are created
        os.makedirs(os.path.join("workspace", "gemini_output"), exist_ok=True)
        os.makedirs("status", exist_ok=True)
        os.makedirs("audit_trail", exist_ok=True)
        os.makedirs("brain", exist_ok=True)
        os.environ["ACTIVE_PROFILE"] = "coder-v2"

    def tearDown(self):
        # Clean up any created test files like STATUS_UPDATE.md
        pass

    def _patch_nodes(self):
        # We start patches here and stop them in tearDown, or use context managers.
        # But for unittest methods it's easier to use decorators.
        pass

    def _setup_run_role_mock(self, mock_run_gemini, mock_run_inspector, mock_run_auditor, mock_graph_run, responses):
        """Routes sequential mock responses to the specific mocked run_role function imports."""
        def gemini_side_effect(*args, **kwargs):
            # Create a fake reasoning.md to bypass the file check natively in gemini_node (since it uses os.path.exists directly)
            with open(os.path.join("workspace", "gemini_output", "reasoning.md"), "w") as f:
                f.write("Fake reasoning")
            response_text = responses["writer"].pop(0)
            return MockCLIResult(response_text)
            
        def inspector_side_effect(*args, **kwargs):
            response_text = responses["inspector"].pop(0)
            return MockCLIResult(response_text)
            
        def auditor_side_effect(*args, **kwargs):
            response_text = responses["reviewer"].pop(0)
            return MockCLIResult(response_text)

        mock_run_gemini.side_effect = gemini_side_effect
        mock_run_inspector.side_effect = inspector_side_effect
        mock_run_auditor.side_effect = auditor_side_effect
        mock_graph_run.side_effect = auditor_side_effect

    # We apply patches for the agent_runner imports
    @patch("system.graph.commit_step")
    @patch("system.nodes.auditor_node.get_full_diff", return_value="+ dummy")
    @patch("system.nodes.inspector_node.get_diff_stat", return_value="1 file changed")
    @patch("system.reporter.get_diff_stat", return_value="1 file changed")
    @patch("system.nodes.gemini_node.get_prompt_template", return_value="Dummy Writer")
    @patch("system.nodes.inspector_node.get_prompt_template", return_value="Dummy Inspector")
    @patch("system.nodes.auditor_node.get_prompt_template", return_value="Dummy Reviewer")
    @patch("system.graph.run_role")
    @patch("system.nodes.gemini_node.run_role")
    @patch("system.nodes.inspector_node.run_role")
    @patch("system.nodes.auditor_node.run_role")
    def test_scenario_1_happy_path(self, mock_run_auditor, mock_run_inspector, mock_run_gemini, mock_graph_run,
                                   mock_gt_auditor, mock_gt_inspector, mock_gt_gemini, 
                                   mock_rep_diff_stat, mock_ins_diff_stat, mock_aud_full_diff, mock_commit):
        """Scenario 1: Happy path (all PASS, all NONE)"""
        responses = {
            "writer": ['```json\n{"status": "ready", "reasoning": "done"}\n```'],
            "inspector": ["PASS\nAll good."],
            "reviewer": [
                '```json\n{"severity": "NONE", "issue": "None", "why_it_matters": "", "suggested_fix": ""}\n```',
                "AGENTS APPEND: No new insights." # architectural logic append
            ]
        }
        self._setup_run_role_mock(mock_run_gemini, mock_run_inspector, mock_run_auditor, mock_graph_run, responses)

        initial_state = {
            "step_number": 1,
            "current_task": "Test Task",
            "loop_count": 0,
            "session_turn_count": 0,
            "gemini_session_id": "none",
            "claude_session_id": "claude123"
        }

        # Run Graph
        result = self.app.invoke(initial_state, self.config)

        # Asserts
        self.assertEqual(result["step_number"], 2)
        self.assertEqual(result["loop_count"], 0)
        self.assertIsNone(result["gemini_session_id"])  # Cleaned writer session
        self.assertEqual(result["claude_session_id"], "claude123") # Persisted claude session
        mock_commit.assert_called_once_with("Step 1: Test Task")
        
        # Check files were produced
        self.assertTrue(os.path.exists(os.path.join("status", "STATUS_UPDATE.md")))
        self.assertTrue(os.path.exists(os.path.join("status", "step-1-summary.md")))

    @patch("system.graph.commit_step")
    @patch("system.nodes.auditor_node.get_full_diff", return_value="+ dummy")
    @patch("system.nodes.inspector_node.get_diff_stat", return_value="1 file changed")
    @patch("system.reporter.get_diff_stat", return_value="1 file changed")
    @patch("system.nodes.gemini_node.get_prompt_template", return_value="Dummy Writer")
    @patch("system.nodes.inspector_node.get_prompt_template", return_value="Dummy Inspector")
    @patch("system.nodes.auditor_node.get_prompt_template", return_value="Dummy Reviewer")
    @patch("system.graph.run_role")
    @patch("system.nodes.gemini_node.run_role")
    @patch("system.nodes.inspector_node.run_role")
    @patch("system.nodes.auditor_node.run_role")
    def test_scenario_2_inspector_incomplete(self, mock_run_auditor, mock_run_inspector, mock_run_gemini, mock_graph_run,
                                   mock_gt_auditor, mock_gt_inspector, mock_gt_gemini, 
                                   mock_rep_diff_stat, mock_ins_diff_stat, mock_aud_full_diff, mock_commit):
        """Scenario 2: Inspector INCOMPLETE → Gemini loop → PASS"""
        responses = {
            "writer": [
                '{"status": "ready", "reasoning": "try 1"}', 
                '{"status": "ready", "reasoning": "try 2"}'
            ],
            "inspector": [
                "INCOMPLETE: Missed variable assignment.",
                "PASS\nAll good."
            ],
            "reviewer": [
                '{"severity": "NONE", "issue": "None", "why_it_matters": "", "suggested_fix": ""}',
                "AGENTS APPEND: No new insights."
            ]
        }
        self._setup_run_role_mock(mock_run_gemini, mock_run_inspector, mock_run_auditor, mock_graph_run, responses)

        initial_state = {"step_number": 1, "gemini_session_id": "none", "loop_count": 0}
        result = self.app.invoke(initial_state, self.config)

        self.assertEqual(result["step_number"], 2)
        self.assertIsNone(result.get("last_error"))
        self.assertEqual(mock_run_gemini.call_count, 2)
        self.assertEqual(mock_run_inspector.call_count, 2)
        self.assertEqual(mock_run_auditor.call_count, 1)
        self.assertEqual(mock_graph_run.call_count, 1)

    @patch("system.graph.commit_step")
    @patch("system.nodes.auditor_node.get_full_diff", return_value="+ dummy")
    @patch("system.nodes.inspector_node.get_diff_stat", return_value="1 file changed")
    @patch("system.reporter.get_diff_stat", return_value="1 file changed")
    @patch("system.nodes.gemini_node.get_prompt_template", return_value="Dummy Writer")
    @patch("system.nodes.inspector_node.get_prompt_template", return_value="Dummy Inspector")
    @patch("system.nodes.auditor_node.get_prompt_template", return_value="Dummy Reviewer")
    @patch("system.graph.run_role")
    @patch("system.nodes.gemini_node.run_role")
    @patch("system.nodes.inspector_node.run_role")
    @patch("system.nodes.auditor_node.run_role")
    def test_scenario_3_auditor_minor(self, mock_run_auditor, mock_run_inspector, mock_run_gemini, mock_graph_run,
                                   mock_gt_auditor, mock_gt_inspector, mock_gt_gemini, 
                                   mock_rep_diff_stat, mock_ins_diff_stat, mock_aud_full_diff, mock_commit):
        """Scenario 3: Auditor MINOR → Gemini targeted fix → NONE"""
        responses = {
            "writer": ['{"status": "ready"}', '{"status": "ready"}'],
            "inspector": ["PASS", "PASS"],
            "reviewer": [
                '{"severity": "MINOR", "issue": "Typo", "why_it_matters": "", "suggested_fix": "Fix"}',
                '{"severity": "NONE", "issue": "Fixed", "why_it_matters": "", "suggested_fix": ""}',
                "AGENTS APPEND"
            ]
        }
        self._setup_run_role_mock(mock_run_gemini, mock_run_inspector, mock_run_auditor, mock_graph_run, responses)

        initial_state = {"step_number": 1, "loop_count": 0}
        result = self.app.invoke(initial_state, self.config)

        self.assertEqual(result["step_number"], 2)
        self.assertEqual(mock_run_gemini.call_count, 2)
        self.assertEqual(mock_run_inspector.call_count, 2)
        self.assertEqual(mock_run_auditor.call_count, 2)
        self.assertEqual(mock_graph_run.call_count, 1)

    @patch("system.graph.commit_step")
    @patch("system.nodes.auditor_node.get_full_diff", return_value="+ dummy")
    @patch("system.nodes.inspector_node.get_diff_stat", return_value="1 file changed")
    @patch("system.reporter.get_diff_stat", return_value="1 file changed")
    @patch("system.nodes.gemini_node.get_prompt_template", return_value="Dummy Writer")
    @patch("system.nodes.inspector_node.get_prompt_template", return_value="Dummy Inspector")
    @patch("system.nodes.auditor_node.get_prompt_template", return_value="Dummy Reviewer")
    @patch("system.graph.run_role")
    @patch("system.nodes.gemini_node.run_role")
    @patch("system.nodes.inspector_node.run_role")
    @patch("system.nodes.auditor_node.run_role")
    def test_scenario_4_auditor_critical(self, mock_run_auditor, mock_run_inspector, mock_run_gemini, mock_graph_run,
                                   mock_gt_auditor, mock_gt_inspector, mock_gt_gemini, 
                                   mock_rep_diff_stat, mock_ins_diff_stat, mock_aud_full_diff, mock_commit):
        """Scenario 4: Auditor CRITICAL → CEO interrupt"""
        responses = {
            "writer": ['{"status": "ready"}'],
            "inspector": ["PASS"],
            "reviewer": [
                '{"severity": "CRITICAL", "issue": "Big Bug", "why_it_matters": "", "suggested_fix": ""}'
            ]
        }
        self._setup_run_role_mock(mock_run_gemini, mock_run_inspector, mock_run_auditor, mock_graph_run, responses)

        initial_state = {"step_number": 1, "loop_count": 0}
        
        # In a real environment, getting interrupted pauses state.
        result = self.app.invoke(initial_state, self.config)

        current_state = self.app.get_state(self.config).values
        self.assertEqual(current_state["claude_audit"]["severity"], "CRITICAL")
        self.assertTrue(current_state.get("ceo_interrupt_flag", False))
        mock_commit.assert_not_called()

if __name__ == "__main__":
    unittest.main()
