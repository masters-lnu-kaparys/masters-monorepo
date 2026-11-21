"""Fresh verification receipt; preserve all earlier frozen test receipts."""
import io
import json
import sys
import unittest
from pathlib import Path
from prepare_data import DOCS,sha256

def main():
    modules=('test_prepare_data','test_methods','test_refinement','test_novelty_audit','test_episode_pair_certificate')
    stream=io.StringIO();suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in modules)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);log=stream.getvalue();print(log)
    receipt={'created_on':'2026-10-25','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
      'skipped':len(result.skipped),'passed':result.wasSuccessful(),
      'test_sha256':{n+'.py':sha256(Path(__file__).parent/(n+'.py')) for n in modules},
      'test_log':log,'final_test_read':False,'old_test_receipts_overwritten':False}
    (DOCS/'phase3-novelty-verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not result.wasSuccessful():sys.exit(1)

if __name__=='__main__':main()
