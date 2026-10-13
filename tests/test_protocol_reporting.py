import json,tempfile,unittest,time
from pathlib import Path
from ppbench.protocol import load_protocol,validate_selection
from ppbench.crossreport import publication_guard,cross_summary
from ppbench.resources import ProcessTreeMonitor
ROOT=Path(__file__).resolve().parents[1]
class ProtocolTests(unittest.TestCase):
    def test_frozen_protocol(self):
        p,identity=load_protocol(ROOT/'configs/protocol.json')
        self.assertEqual(len(identity['protocol_sha256']),64)
        with self.assertRaises(ValueError):validate_selection(p,'nslkdd',500000)
        with tempfile.TemporaryDirectory() as d:
            p['paillier_bits']=128;f=Path(d)/'p.json';f.write_text(json.dumps(p))
            with self.assertRaises(ValueError):load_protocol(f)
    def test_smoke_cannot_publish(self):
        r=json.loads((ROOT/'results/smoke-20261013/run.json').read_text())
        with self.assertRaises(ValueError):publication_guard(r)
    def test_numeric_csv(self):
        with tempfile.TemporaryDirectory() as d:
            rows=cross_summary([ROOT/'results/smoke-20261013/run.json'],d)
            self.assertTrue(rows)
            self.assertTrue(all(isinstance(x['median'],(int,float)) for x in rows))
            self.assertTrue((Path(d)/'cross-size-summary.csv').exists())
    def test_resource_monitor(self):
        m=ProcessTreeMonitor(.005).start();time.sleep(.025);r=m.stop()
        if r['available']:
            self.assertGreater(r['peak_tree_rss_bytes'],0)
            self.assertGreaterEqual(r['snapshots'],2)
            self.assertGreaterEqual(r['tree_cpu_seconds'],0)
if __name__=='__main__':unittest.main()
