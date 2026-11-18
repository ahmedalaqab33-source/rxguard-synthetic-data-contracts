"""Run reviewed invented-data tests only; no raw-data or network operations."""
from pathlib import Path
import os, subprocess, sys
ROOT=Path(__file__).resolve().parent
TESTS=[
 ('tools/clinical_data_contract_v1','test_contract.py'),
 ('tools/clinical_data_contract_v1','test_emar_linkage_v1.py'),
 ('tools/clinical_data_contract_v1','test_admission_medication_coverage_v1.py'),
 ('tools/creatinine_synthetic_v1','test_comparison.py'),
 ('tools/medication_linkage_synthetic_v1','test_linkage.py'),
 ('tools/parallel_readiness_v1','test_integration.py'),
 ('tools/evidence_trace_synthetic_v1','test_trace.py'),
]
def main():
 for folder,name in TESTS:
  command=[sys.executable,'-B',str(ROOT/folder/name)]
  result=subprocess.run(command,cwd=ROOT/folder,check=False,timeout=120,
      env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  if result.returncode:return result.returncode
 return 0
if __name__=='__main__':raise SystemExit(main())
