import json
import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import generate_summary

class TestSummaryGeneration(unittest.TestCase):
    def setUp(self):
        self.summary_file = "test_summary.json"
        self.csv_file = "test_historical_spread.csv"
        generate_summary.SUMMARY_FILE = self.summary_file
        generate_summary.CSV_FILE = self.csv_file
        generate_summary.API_KEY = "dummy_key"
        
        # Create a dummy CSV
        with open(self.csv_file, "w", encoding="utf-8") as f:
            f.write("date,yield_2y,yield_5y,spread,mortgage_5y,lending_margin\n")
            f.write("2026-03-26,2.99,3.20,0.21,3.94,0.74\n")

    def tearDown(self):
        if os.path.exists(self.summary_file):
            os.remove(self.summary_file)
        if os.path.exists(self.csv_file):
            os.remove(self.csv_file)

    @patch("google.genai.Client")
    def test_generate_summary_history(self, mock_client_class):
        # Mocking the client and its response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "New summary text."
        mock_client.models.generate_content.return_value = mock_response

        # Scenario 1: No previous summary
        generate_summary.generate_summary()
        
        with open(self.summary_file, "r") as f:
            data = json.load(f)
            self.assertEqual(data["summary"], "New summary text.")
            self.assertEqual(len(data["history"]), 1)
            self.assertEqual(data["history"][0]["summary"], "New summary text.")

        # Scenario 2: Previous summary exists (Migration)
        with open(self.summary_file, "w") as f:
            json.dump({
                "summary": "Old summary",
                "last_updated": "2026-03-25 08:00:00"
            }, f)
        
        # Force cache to be old
        with patch("generate_summary.get_mountain_time") as mock_mt:
            mock_mt.return_value = datetime.now() + timedelta(hours=3)
            generate_summary.generate_summary()

        with open(self.summary_file, "r") as f:
            data = json.load(f)
            self.assertEqual(len(data["history"]), 2)
            # history should be sorted newest first
            self.assertEqual(data["history"][1]["summary"], "Old summary")
            self.assertEqual(data["history"][0]["summary"], "New summary text.")

    def test_history_limit(self):
        # Test that history keeps only 10 items
        history = []
        for i in range(15):
            history.append({
                "date": f"2026-03-{i+1:02} 08:00:00",
                "summary": f"Summary {i}"
            })
        
        with open(self.summary_file, "w") as f:
            json.dump({
                "summary": "Summary 14",
                "last_updated": "2026-03-15 08:00:00",
                "history": history
            }, f)

        # Mock generate_summary dependencies
        with patch("google.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = "Newest summary."
            mock_client.models.generate_content.return_value = mock_response

            with patch("generate_summary.get_mountain_time") as mock_mt:
                mock_mt.return_value = datetime.now() + timedelta(days=20)
                generate_summary.generate_summary()

        with open(self.summary_file, "r") as f:
            data = json.load(f)
            self.assertEqual(len(data["history"]), 10)
            self.assertEqual(data["history"][0]["summary"], "Newest summary.")

if __name__ == "__main__":
    unittest.main()
