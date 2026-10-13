import contextlib,io,json,tempfile,unittest
from pathlib import Path
from ppbench.benchmark import run,atomic_json
from ppbench.datasets import synthetic
from ppbench.model import NYC_NUMERIC,NYC_VISIBLE

class ResumeTests(unittest.TestCase):
    def test_checkpoint_resume_and_mismatch_rejection(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            args=(synthetic(3),NYC_NUMERIC,NYC_VISIBLE,'payment_type',['PLAIN','H-CHAOS'],d)
            kw={'repeats':2,'warmups':0,'bits':64,'test_only':True,'provenance':{'kind':'synthetic','seed':2024}}
            first=run(*args,**kw); self.assertEqual(len(first['samples']),4)
            path=Path(d)/'checkpoint.json';cp=json.loads(path.read_text());retained=cp['samples'][0]
            cp['samples']=[retained];cp['state']='in_progress';atomic_json(path,cp)
            resumed=run(*args,**kw,resume=True)
            self.assertEqual(len(resumed['samples']),4);self.assertEqual(resumed['samples'][0],retained)
            self.assertEqual(len(resumed['execution_sessions']),2);self.assertEqual(resumed['state'],'complete')
            self.assertEqual(len({(s['config'],s['repeat']) for s in resumed['samples']}),4)
            with self.assertRaises(ValueError):run(*args,**{**kw,'repeats':3},resume=True)
            with self.assertRaises(ValueError):run(*args,**kw)
            complete=run(*args,**kw,resume=True);self.assertEqual(complete['samples'],resumed['samples'])
