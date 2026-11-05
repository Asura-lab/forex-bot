import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class DiscoveryCliTests(unittest.TestCase):
    def test_feasibility_run_is_explicitly_h4_only_and_records_risk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'synthetic.csv'
            with source.open('w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['time', 'open', 'high', 'low', 'close', 'spread'])
                for i in range(5000):
                    p = 1.1 + i * .00001
                    writer.writerow([1704067200 + i * 900, p, p + .0001, p - .0001, p + .00005, 10])
            output = root / 'report'
            process = subprocess.run([sys.executable, '-m', 'forexbot.discovery', str(source),
                                      '--selection-bars', '3500', '--development-bars', '4200',
                                      '--risk-fraction', '.01', '--timeframe-seconds', '14400',
                                      '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            report = json.loads((output / 'summary.json').read_text())
            self.assertEqual(len(report['candidates']), 3)
            self.assertTrue(all(c['spec']['seconds'] == 14400 and c['base_config']['risk_fraction'] == .01
                                for c in report['candidates']))
            self.assertFalse(report['deployment_ready'])


if __name__ == '__main__':
    unittest.main()
