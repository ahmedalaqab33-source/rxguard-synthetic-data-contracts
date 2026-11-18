"""Execute only new eMAR linkage tests and a fixed invented aggregate fixture."""
import argparse,hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from emar_linkage_v1 import ROOT,VERSION,summarize,invented_fixture

def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False)

def main(out):
    out.mkdir(parents=True,exist_ok=False)
    cmd=[sys.executable,'-B',str(ROOT/'test_emar_linkage_v1.py')]
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    (out/'tests_stdout.txt').write_text(proc.stdout,encoding='utf-8');(out/'tests_stderr.txt').write_text(proc.stderr,encoding='utf-8')
    receipt={'created_utc':datetime.now(timezone.utc).isoformat(),'scope':'SYNTHETIC','version':VERSION,'command':cmd,'exit_code':proc.returncode,'raw_source_accessed':False,'gates':{'CLINICAL_ACCEPTANCE':'HOLD','AKI_ENDPOINT_READY':False,'ML_TRAINING_PERMITTED':False}}
    if proc.returncode:
        receipt['status']='FAIL';write(out/'execution_receipt.json',receipt);raise RuntimeError('New eMAR linkage tests failed')
    p=invented_fixture();result=summarize(p);write(out/'invented_fixture.json',p);write(out/'aggregate_counts.json',result)
    receipt.update(status='PASS',new_test_methods=8,results=result,python=sys.version,code_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['emar_linkage_v1.py','emar_linkage_v1.sql','test_emar_linkage_v1.py','run_emar_linkage_v1.py']})
    write(out/'execution_receipt.json',receipt);print(json.dumps({'status':'PASS','new_tests':8,'results':result}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);main(ap.parse_args().output)
