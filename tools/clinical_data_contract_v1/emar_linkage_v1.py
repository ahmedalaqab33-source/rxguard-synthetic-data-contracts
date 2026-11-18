"""Synthetic-only executable harness for reusable eMAR composite-key SQL."""
from pathlib import Path
import duckdb
VERSION='synthetic-emar-linkage-0.1.0'
ROOT=Path(__file__).resolve().parent
KEYS={'scope','row_id','subject_id','emar_id','emar_seq'}

def validate(packet):
    if not isinstance(packet,dict) or set(packet)!={'scope','invented','parents','details'} or packet['scope']!='SYNTHETIC' or packet['invented'] is not True:raise ValueError('Explicit invented envelope required')
    for name in ['parents','details']:
        rows=packet[name]
        if not isinstance(rows,list) or len(rows)>1000:raise ValueError('Bounded row list required')
        seen=set()
        for row in rows:
            if not isinstance(row,dict) or set(row)!=KEYS or row['scope']!='SYNTHETIC':raise ValueError('Exact marked row schema required')
            rid=row['row_id']
            if not isinstance(rid,str) or not rid.startswith('INVENTED-') or len(rid)>100 or rid in seen:raise ValueError('Unique invented row key required')
            seen.add(rid)
            for k in ['subject_id','emar_seq']:
                v=row[k]
                if v is not None and (type(v) is not int or v<0 or v>=2**63):raise ValueError('Nonnegative integer/null key required')
            v=row['emar_id']
            if v is not None and (not isinstance(v,str) or not v.strip() or len(v)>100):raise ValueError('Nonempty bounded emar_id or null required')

def summarize(packet):
    validate(packet)
    with duckdb.connect(':memory:') as con:
        for name in ['parents','details']:
            con.execute('CREATE TABLE '+name+' (row_id VARCHAR,subject_id BIGINT,emar_id VARCHAR,emar_seq BIGINT)')
            rows=[[x[k] for k in ['row_id','subject_id','emar_id','emar_seq']] for x in packet[name]]
            if rows:con.executemany('INSERT INTO '+name+' VALUES (?,?,?,?)',rows)
        result=dict(con.execute((ROOT/'emar_linkage_v1.sql').read_text()).fetchall())
    if result['detail_rows']!=result['classified_detail_rows']:raise AssertionError('Fanout or lost details')
    if result['detail_rows']!=sum(result[k] for k in ['missing_key_detail_rows','orphan_detail_rows','ambiguous_parent_detail_rows','unique_parent_link_detail_rows']):raise AssertionError('Nonexhaustive classification')
    return result

def invented_fixture():
    def row(i,key):return dict(scope='SYNTHETIC',row_id='INVENTED-'+str(i),subject_id=key[0],emar_id=key[1],emar_seq=key[2])
    return dict(scope='SYNTHETIC',invented=True,parents=[row(i,k) for i,k in enumerate([(1,'A',1),(2,'B',1),(2,'B',1),(3,'C',1),(None,'M',1),(4,'D',1),(1,'A',2)])],details=[row(i,k) for i,k in enumerate([(1,'A',1),(1,'A',1),(2,'B',1),(9,'X',1),(None,'M',1),(1,'A',2),(8,'A',1),(4,'D',1)])])
