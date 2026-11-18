"""Invented dictionary/event join contract; no restricted-source loader."""
from pathlib import Path
from datetime import datetime
import json
import duckdb
VERSION='synthetic-dictionary-event-0.1.0'
ROOT=Path(__file__).resolve().parent
DKEYS={'scope','itemid','label','category','linksto','unitname'}
EKEYS={'scope','row_id','itemid','amountuom','statusdescription','starttime','endtime','storetime'}

def timestamp(value):
    if not isinstance(value,str):raise ValueError('Timestamp must be a canonical string')
    try:d=datetime.strptime(value,'%Y-%m-%d %H:%M:%S')
    except ValueError:raise ValueError('Invalid timestamp') from None
    if d.strftime('%Y-%m-%d %H:%M:%S')!=value:raise ValueError('Noncanonical timestamp')
    return d

def validate(p):
    if not isinstance(p,dict) or set(p)!={'scope','invented','contract_version','as_of','dictionary','events'}:raise ValueError('Exact invented envelope required')
    if p['scope']!='SYNTHETIC' or p['invented'] is not True or p['contract_version']!=VERSION:raise ValueError('Explicit invented/version marking required')
    timestamp(p['as_of'])
    for name,keys in [('dictionary',DKEYS),('events',EKEYS)]:
        rows=p[name]
        if not isinstance(rows,list) or len(rows)>1000:raise ValueError('Bounded record list required')
        for row in rows:
            if not isinstance(row,dict) or set(row)!=keys or row['scope']!='SYNTHETIC':raise ValueError('Exact marked record schema required')
            if row['itemid'] is not None and (type(row['itemid']) is not int or not 0<row['itemid']<2**31):raise ValueError('Positive integer item key required')
            for k,v in row.items():
                if k!='itemid' and v is not None and (not isinstance(v,str) or not v.strip() or len(v)>200):raise ValueError('Bounded nonempty string or null required')
            if name=='events':
                if not isinstance(row['row_id'],str) or not row['row_id'].startswith('INVENTED-'):raise ValueError('Invented unique row ID required')
                for k in ['starttime','endtime','storetime']:
                    if row[k] is not None:timestamp(row[k])
    ids=[x['row_id'] for x in p['events']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate synthetic event row IDs')

def load_fixture():
    p=json.loads((ROOT/'invented_fixture.json').read_text(encoding='utf-8'));validate(p);return p

def evaluate(p):
    validate(p)
    with duckdb.connect(':memory:') as con:
        con.execute('CREATE TABLE dictionary(scope VARCHAR,itemid INTEGER,label VARCHAR,category VARCHAR,linksto VARCHAR,unitname VARCHAR)')
        con.execute('CREATE TABLE events(scope VARCHAR,row_id VARCHAR,itemid INTEGER,amountuom VARCHAR,statusdescription VARCHAR,starttime TIMESTAMP,endtime TIMESTAMP,storetime TIMESTAMP)')
        if p['dictionary']:con.executemany('INSERT INTO dictionary VALUES (?,?,?,?,?,?)',[[x[k] for k in ['scope','itemid','label','category','linksto','unitname']] for x in p['dictionary']])
        if p['events']:con.executemany('INSERT INTO events VALUES (?,?,?,?,?,?,?,?)',[[x[k] for k in ['scope','row_id','itemid','amountuom','statusdescription','starttime','endtime','storetime']] for x in p['events']])
        cur=con.execute((ROOT/'contract.sql').read_text(),[p['as_of']]);names=[x[0] for x in cur.description];rows=[dict(zip(names,x)) for x in cur.fetchall()]
    if len(rows)!=len(p['events']) or len({x['row_id'] for x in rows})!=len(rows):raise AssertionError('Join cardinality violated')
    return rows

STATES={'linkage_state':['MISSING_KEY','UNMATCHED_KEY','AMBIGUOUS_DICTIONARY_KEY','UNKNOWN_LINKSTO','LINKSTO_MISMATCH','UNIQUE_INPUTEVENTS_LINK'],'unit_state':['NOT_ASSESSED','UNKNOWN','LITERAL_MATCH','LITERAL_MISMATCH'],'interval_state':['UNKNOWN','REVERSED','NONREVERSED'],'availability_state':['UNKNOWN','AT_OR_BEFORE','AFTER'],'status_state':['MISSING_UNINTERPRETED','PRESENT_UNINTERPRETED']}
def aggregate(p,rows):
    result={'dictionary_rows':len(p['dictionary']),'dictionary_null_key_rows':sum(x['itemid'] is None for x in p['dictionary']),'dictionary_distinct_nonnull_keys':len({x['itemid'] for x in p['dictionary'] if x['itemid'] is not None}),'event_rows':len(p['events']),'output_rows':len(rows)}
    keys=[x['itemid'] for x in p['dictionary'] if x['itemid'] is not None]
    result['dictionary_duplicate_keys']=sum(keys.count(k)>1 for k in set(keys))
    for field,states in STATES.items():
        for state in states:result[field+'.'+state]=sum(x[field]==state for x in rows)
    return result
