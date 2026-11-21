"""Reproducible test receipt; does not load any experimental data partitions."""
import io
import json
import platform
import sys
import unittest
from importlib.metadata import version
from pathlib import Path
from prepare_data import DOCS,sha256

def main():
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromName('test_prepare_data'),unittest.defaultTestLoader.loadTestsFromName('test_methods')])
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    log=stream.getvalue();print(log)
    receipt={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
      'skipped':len(result.skipped),'successful':result.wasSuccessful(),
      'python':platform.python_version(),'packages':{n:version(n) for n in ('numpy','numba','scipy','duckdb','matplotlib')},
      'test_code_sha256':{p.name:sha256(p) for p in (Path(__file__).parent/'test_methods.py',Path(__file__).parent/'test_prepare_data.py')},
      'coverage':'Data preparation, independent simulator equivalence, causal interface, boundary labels, LP equations and published example, training context, feature pooling, selection rules',
      'test_log':log}
    (DOCS/'phase3-verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not result.wasSuccessful():sys.exit(1)

if __name__=='__main__':main()
