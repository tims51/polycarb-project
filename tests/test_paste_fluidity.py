import sys
import os
import unittest
from unittest.mock import MagicMock

# Add app directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

# Mock streamlit before importing the component
mock_st = MagicMock()
mock_st.session_state = {}
sys.modules["streamlit"] = mock_st

# Now import the widget
from components.paste_fluidity_widget import PasteFluidityWidget

class TestPasteFluidityWidget(unittest.TestCase):
    def setUp(self):
        mock_st.session_state = {}
        self.key_prefix = "test_prefix"
        self.widget = PasteFluidityWidget(self.key_prefix)
    
    def test_initialization(self):
        self.assertEqual(self.widget.key_prefix, self.key_prefix)
        self.assertIn("initial", self.widget.metrics_config)
        self.assertIn("2h", self.widget.metrics_config)
        
    def test_configuration_toggle(self):
        # Setup session state
        config_key = f"{self.key_prefix}_config_show_timeseries"
        mock_st.session_state[config_key] = True
        
        # Call render_configuration
        self.widget.render_configuration()
        # Verify checkbox was called with correct key
        mock_st.checkbox.assert_called()
        call_args = mock_st.checkbox.call_args
        self.assertEqual(call_args[1]['key'], config_key)
        
    def test_get_data_basic_only(self):
        # Configure to show only basic (timeseries=False)
        config_key = f"{self.key_prefix}_config_show_timeseries"
        mock_st.session_state[config_key] = False
        
        # Simulate user input in session state
        input_key = f"{self.key_prefix}_flow_initial_mm"
        mock_st.session_state[input_key] = 225.0
        
        # Simulate hidden inputs existing in state (e.g. from previous run) but ignored/zeroed by logic?
        # Actually get_data logic checks if metric_id in active_metrics.
        # If it's NOT in active_metrics, it returns 0.0 regardless of session_state?
        # Let's verify that behavior.
        hidden_key = f"{self.key_prefix}_flow_1h_mm"
        mock_st.session_state[hidden_key] = 180.0
        
        data = self.widget.get_data()
        
        self.assertEqual(data["flow_initial_mm"], 225.0)
        self.assertEqual(data["flow_1h_mm"], 0.0) # Should be 0 because timeseries is disabled
        
    def test_get_data_with_timeseries(self):
        # Configure to show timeseries
        config_key = f"{self.key_prefix}_config_show_timeseries"
        mock_st.session_state[config_key] = True
        
        # Simulate inputs
        mock_st.session_state[f"{self.key_prefix}_flow_initial_mm"] = 225.0
        mock_st.session_state[f"{self.key_prefix}_flow_1h_mm"] = 180.0
        
        data = self.widget.get_data()
        
        self.assertEqual(data["flow_initial_mm"], 225.0)
        self.assertEqual(data["flow_1h_mm"], 180.0)

    def test_get_data_production_mode(self):
        # Configure to show timeseries
        config_key = f"{self.key_prefix}_config_show_timeseries"
        mock_st.session_state[config_key] = True
        
        # Simulate Standard Sample inputs
        mock_st.session_state[f"{self.key_prefix}_std_flow_initial_mm"] = 230.0
        mock_st.session_state[f"{self.key_prefix}_std_flow_1h_mm"] = 190.0
        
        data = self.widget.get_data()
        
        self.assertEqual(data["std_flow_initial_mm"], 230.0)
        self.assertEqual(data["std_flow_1h_mm"], 190.0)

    def test_performance_benchmark(self):
        import time
        start_time = time.time()
        
        # Simulate rendering 100 times
        for _ in range(100):
            self.widget.render_input_section("性能对比测试")
            
        end_time = time.time()
        avg_time = (end_time - start_time) / 100
        
        # Expect very fast rendering (mocked)
        self.assertLess(avg_time, 0.01) # Should be < 10ms per render

if __name__ == '__main__':
    unittest.main()
