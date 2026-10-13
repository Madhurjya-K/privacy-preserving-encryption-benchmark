import copy,secrets,unittest
from ppbench.crypto import keygen
from ppbench.model import Keys,NYC_NUMERIC,NYC_VISIBLE
from ppbench.pipeline import *
from ppbench.integrity import partition_hash

class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys=Keys(keygen(128,test_only=True),bytes(32),b'c'*32,b'm'*32)
        cls.rows=[{'fare_amount':'-1.235','trip_distance':'1.20','tip_amount':None,'payment_type':0,'VendorID':1,'secret':'CANARY_58fcd'},
                  {'fare_amount':'2.225','trip_distance':'2.345','tip_amount':None,'payment_type':0,'VendorID':1,'secret':'CANARY_993a'},
                  {'fare_amount':None,'trip_distance':'0.00','tip_amount':'-0.50','payment_type':1,'VendorID':2,'secret':'CANARY_310a'}]
    def bundle(self,config='H-CHAOS'):
        return protect(self.rows,config,self.keys,NYC_NUMERIC,NYC_VISIBLE,partition_size=2)
    def test_correctness_configs_null_semantics(self):
        configs=['PLAIN','H-CHAOS']
        try:import cryptography;configs+=['AES-DEC','H-GCM']
        except ImportError:pass
        answers=[]
        for config in configs:
            b=self.bundle(config);self.assertTrue(verify(b,self.keys))
            answers.append(finalize(query(b,self.keys,'payment_type'),b,self.keys))
        for a in answers:self.assertEqual(a,answers[0])
        f=answers[0]['0']['fields'];self.assertEqual(f['fare_amount']['sum'],'0.98');self.assertEqual(f['fare_amount']['avg'],'0.49')
        self.assertEqual(answers[0]['0']['count_star'],2)
        self.assertIsNone(f['tip_amount']['sum']);self.assertIsNone(f['tip_amount']['avg']);self.assertEqual(f['tip_amount']['count_nonnull'],0)
        b=self.bundle();a=finalize(query(b,self.keys,None),b,self.keys)['ALL']
        self.assertEqual(a['count_star'],3);self.assertEqual(a['fields']['fare_amount']['count_nonnull'],2)
    def test_hidden_group_rejected(self):
        with self.assertRaises(ValueError):query(self.bundle(),self.keys,'secret')
    def test_hybrid_roundtrip(self):
        rows=materialize(self.bundle(),self.keys)
        self.assertEqual(rows[0]['secret'],self.rows[0]['secret']);self.assertEqual(rows[0]['fare_amount'],'-1.24')
    def test_tamper_classes(self):
        baseline=self.bundle()
        def flip(b):b['partitions'][0][0]['chaos']='00'+b['partitions'][0][0]['chaos'][2:]
        def delete(b):b['partitions'][0].pop()
        def insert(b):b['partitions'][0].append({'id':'new'})
        def duplicate(b):b['partitions'][0].append(copy.deepcopy(b['partitions'][0][0]))
        def swap(b):b['partitions'].reverse()
        def move(b):b['partitions'][1].append(b['partitions'][0].pop())
        def replace_digest(b):
            b['partitions'][0][0]['id']='replaced'
            b['manifest']['body']['partitions'][1]['sha256']=partition_hash(b['partitions'][0])
        def metadata(b):b['metadata']['bounds']['fare_amount']=0
        def nonce(b):b['partitions'][0][0]['nonce']='00'*12
        def ciphertext(b):b['partitions'][0][0]['numbers']['fare_amount']='1'
        for attack in (flip,delete,insert,duplicate,swap,move,replace_digest,metadata,nonce,ciphertext):
            with self.subTest(attack=attack.__name__):
                b=copy.deepcopy(baseline);attack(b)
                with self.assertRaises(ValueError):verify(b,self.keys)
    def test_owner_rollback_and_manifest_tamper(self):
        b=self.bundle()
        for kwargs in ({'owner':'another'},{'version':2}):
            with self.assertRaises(ValueError):verify(b,self.keys,**kwargs)
        b['manifest']['hmac_sha256']='0'*64
        with self.assertRaises(ValueError):verify(b,self.keys)
    def test_within_partition_reorder_intentionally_not_detected(self):
        b=self.bundle();b['partitions'][0].reverse();self.assertTrue(verify(b,self.keys))
    def test_bad_backend_no_fallback(self):
        with self.assertRaises(ValueError):query(self.bundle(),self.keys,'payment_type','spark')
