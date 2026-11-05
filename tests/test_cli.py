import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_reports_record_fixed_config_and_chronological_split(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'synthetic.csv'
            with source.open('w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['time', 'open', 'high', 'low', 'close', 'spread'])
                for i in range(200):
                    price = 1.1 + i * .00003
                    writer.writerow([1700000000 + i * 900, price, price + .0001,
                                     price - .0001, price + .00008, 10])
            output = Path(directory) / 'report'
            process = subprocess.run([sys.executable, '-m', 'forexbot', str(source),
                                      '--output', str(output), '--label', 'synthetic-test'],
                                     capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            report = json.loads((output / 'summary.json').read_text())
            self.assertEqual(len(report['data_sha256']), 64)
            self.assertEqual(report['config']['risk_fraction'], .0025)
            self.assertLess(report['development']['last_time'], report['evaluation_start_time'])
            self.assertEqual(report['evaluation']['initial_equity'], 1000)
            self.assertEqual(report['evaluation']['first_time'], report['evaluation_start_time'])
            self.assertEqual(report['evaluation']['evaluated_bars'], 60)
            self.assertTrue((output / 'evaluation-trades.csv').exists())
            self.assertTrue((output / 'evaluation-equity.csv').exists())


if __name__ == '__main__':
    unittest.main()
