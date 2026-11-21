"""Verify old and refined scientific implementations without experimental reads."""
import io
import json
import sys
import unittest
from pathlib import Path
from prepare_data import ROOT,DOCS,sha256

def main():
    stream=io.StringIO()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in ('test_prepare_data','test_methods','test_refinement'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);log=stream.getvalue();print(log)
    receipt={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful(),
      'test_sha256':{n:sha256(Path(__file__).parent/n) for n in ('test_prepare_data.py','test_methods.py','test_refinement.py')},
      'test_log':log,'final_test_read':False}
    (DOCS/'phase3-refinement-verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not result.wasSuccessful():sys.exit(1)

if __name__=='__main__':main()
