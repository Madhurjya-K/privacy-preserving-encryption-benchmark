import json,tempfile,unittest
from pathlib import Path
from ppbench.security import *
from ppbench.report import summary
from ppbench.datasets import NSL_COLUMNS,load_dataset

class SecurityTests(unittest.TestCase):
    def test_sensitivity_and_cycle_bounded(self):
        s=sensitivity(trials=2,length=128);self.assertEqual(len(s),2)
        for row in s:
            self.assertGreater(row['key_hamming_fraction'],0);self.assertGreater(row['nonce_hamming_fraction'],0)
        c=cycle_scan(trials=2,steps=100);self.assertEqual(len(c),2)
        self.assertTrue(all(r['steps_checked']<=100 for r in c))
    def test_nonce_reuse(self):self.assertTrue(nonce_reuse_demo()['xor_leak_confirmed'])
    def test_bounded_recovery_runs(self):
        r=bounded_state_recovery(candidate_bits=8);self.assertTrue(r['true_state_in_matches']);self.assertEqual(r['candidates'],256)
        self.assertGreater(r['holdout_predictions_matching'],0)
    def test_exposure_scope(self):
        r=exposure_audit({'x':'EXPOSURE_CANARY'},['EXPOSURE_CANARY']);self.assertTrue(r['canary_occurrences']['EXPOSURE_CANARY']);self.assertFalse(r['proof'])
    def test_summary(self):
        r=summary([1,2,3,4],bootstrap=100);self.assertEqual(r['median'],2.5);self.assertEqual(r['iqr'],1.5)
    def test_nsl_schema_and_insufficient_size(self):
        self.assertEqual(len(NSL_COLUMNS),43)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'KDDTrain+.txt';p.write_text(','.join(['0']*43)+'\n')
            rows,prov=load_dataset('nslkdd',p,1);self.assertEqual(rows[0]['duration'],0)
            with self.assertRaises(ValueError):load_dataset('nslkdd',p,2)
