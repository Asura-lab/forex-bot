import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ExperimentTests(unittest.TestCase):
    def test_sealed_suffix_does_not_affect_development_performance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = []
            for suffix_price, label in ((1.2, 'a'), (10, 'b')):
                source = root / (label + '.csv')
                with source.open('w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['time', 'open', 'high', 'low', 'close', 'spread'])
                    for i in range(6000):
                        price = 1.1 + i * .00001 if i < 5000 else suffix_price
                        writer.writerow([1704067200 + i * 900, price, price + .0001,
                                         price - .0001, price + .00005, 10])
                output = root / ('report-' + label)
                process = subprocess.run([sys.executable, '-m', 'forexbot.experiment', str(source),
                                          '--development-bars', '5000', '--output', str(output)],
                                         capture_output=True, text=True)
                self.assertEqual(process.returncode, 0, process.stderr)
                reports.append(json.loads((output / 'summary.json').read_text()))
            a, b = reports
            self.assertEqual(a['development_sha256'], b['development_sha256'])
            self.assertNotEqual(a['data_sha256'], b['data_sha256'])
            self.assertEqual(a['cases'], b['cases'])
            self.assertEqual(a['sealed_bars_excluded'], 1000)
            self.assertEqual(len(a['cases']), 16)
            self.assertFalse(a['deployment_ready'])
            self.assertTrue((root / 'report-a' / 'rounds.csv').exists())
            self.assertTrue((root / 'report-a' / 'trades.csv').exists())


if __name__ == '__main__':
    unittest.main()
