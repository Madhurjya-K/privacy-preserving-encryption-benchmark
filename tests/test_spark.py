import os,unittest
from ppbench.crypto import keygen
from ppbench.model import Keys,NYC_NUMERIC,NYC_VISIBLE
from ppbench.datasets import synthetic
from ppbench.pipeline import *

@unittest.skipUnless(os.environ.get('PPBENCH_TEST_SPARK')=='1','opt-in actual Spark integration test; JVM/pyspark required')
class SparkTests(unittest.TestCase):
    def test_real_spark_reduce_matches_python(self):
        from pyspark.sql import SparkSession
        s=SparkSession.builder.master('local[2]').appName('ppbench-test').getOrCreate()
        try:
            keys=Keys(keygen(128,test_only=True),bytes(32),bytes(32),bytes(32))
            for config in ('PLAIN','H-CHAOS','AES-DEC','H-GCM'):
                b=protect(synthetic(8),config,keys,NYC_NUMERIC,NYC_VISIBLE)
                for group in ('payment_type',None):
                    self.assertEqual(finalize(query(b,keys,group,'spark',s),b,keys),finalize(query(b,keys,group),b,keys))
        finally:s.stop()
