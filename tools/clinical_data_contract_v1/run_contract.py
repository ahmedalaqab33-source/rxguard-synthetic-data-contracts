"""Fixed invented fixture only; no source input argument or restricted reader."""
import argparse,csv,hashlib,json,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
import duckdb
from contract import ROOT,VERSION,load_fixture,evaluate,aggregate

def write_json(p,x):
    with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,allow_nan=False)
def write_csv(p,rows,keys):
    with p.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(out,rscript):
    p=load_fixture();rows=evaluate(p);totals=aggregate(p,rows)
    out.mkdir(parents=True,exist_ok=False)
    write_json(out/'python_sql_aggregates.json',totals)
    write_json(out/'run_scope.json',{'scope':'SYNTHETIC','invented':True,'version':VERSION,'as_of':p['as_of'],'raw_source_reads':False,'delivery_classification':'NOT_IMPLEMENTED','clinical_validation':False})
    for name in ['dictionary','events']:write_csv(out/('invented_'+name+'.csv'),p[name],list(p[name][0]))
    write_csv(out/'synthetic_manifest.csv',[{'scope':'SYNTHETIC','invented':'TRUE','contract_version':VERSION,'as_of':p['as_of']}],['scope','invented','contract_version','as_of'])
    paths=[out/'invented_dictionary.csv',out/'invented_events.csv',out/'synthetic_manifest.csv'];before={x.name:digest(x) for x in paths}
    cmd=[str(rscript),'--vanilla',str(ROOT/'check_aggregates.R'),str(out)]
    receipt={'version':VERSION,'scope':'SYNTHETIC','created_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'duckdb':duckdb.__version__,'r_command':cmd,'gates':{'CLINICAL_ACCEPTANCE':'HOLD','AKI_ENDPOINT_READY':False,'ML_TRAINING_PERMITTED':False},'code_hashes':{x.name:digest(x) for x in ROOT.iterdir() if x.is_file()},'raw_source_reads':False}
    try:
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
        (out/'r_stdout.txt').write_text(proc.stdout,encoding='utf-8');(out/'r_stderr.txt').write_text(proc.stderr,encoding='utf-8')
        receipt['r_exit_code']=proc.returncode
        if proc.returncode:raise AssertionError('R failed; inspect preserved stderr')
        with (out/'r_aggregates.csv').open(encoding='utf-8',newline='') as f:rrows=list(csv.DictReader(f))
        if len({x['metric'] for x in rrows})!=len(rrows):raise AssertionError('Duplicate R metric')
        rt={x['metric']:int(x['count']) for x in rrows}
        if rt!=totals:raise AssertionError('Python/SQL and independent R aggregates differ')
        if before!={x.name:digest(x) for x in paths}:raise AssertionError('Invented fixture modified')
        receipt.update(status='PASS',metrics_compared=len(totals),max_absolute_difference=0,fixture_hashes=before)
    except Exception as exc:
        receipt.update(status='FAIL',error=type(exc).__name__+': '+str(exc));raise
    finally:write_json(out/'execution_receipt.json',receipt)
    print(json.dumps({'status':'PASS','event_rows':len(rows),'aggregate_metrics':len(totals),'max_absolute_difference':0}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--rscript',type=Path,default=Path('C:/Program Files/R/R-4.6.1/bin/Rscript.exe'));a=ap.parse_args();run(a.output,a.rscript)
