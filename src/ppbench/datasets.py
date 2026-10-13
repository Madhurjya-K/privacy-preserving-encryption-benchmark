"""Frozen source identities; user downloads are checksummed, not silently fetched."""
import hashlib,json,random
from pathlib import Path
NSL_COLUMNS=('duration,protocol_type,service,flag,src_bytes,dst_bytes,land,wrong_fragment,urgent,hot,num_failed_logins,logged_in,num_compromised,root_shell,su_attempted,num_root,num_file_creations,num_shells,num_access_files,num_outbound_cmds,is_host_login,is_guest_login,count,srv_count,serror_rate,srv_serror_rate,rerror_rate,srv_rerror_rate,same_srv_rate,diff_srv_rate,srv_diff_host_rate,dst_host_count,dst_host_srv_count,dst_host_same_srv_rate,dst_host_diff_srv_rate,dst_host_same_src_port_rate,dst_host_srv_diff_host_rate,dst_host_serror_rate,dst_host_srv_serror_rate,dst_host_rerror_rate,dst_host_srv_rerror_rate,label,difficulty').split(',')
NYC_COLUMNS=['fare_amount','trip_distance','tip_amount','payment_type','VendorID','tpep_pickup_datetime','tpep_dropoff_datetime','PULocationID','DOLocationID']

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()

def load_dataset(kind,path,size,seed=2024):
    path=Path(path)
    if kind=='nyc':
        import pandas as pd
        df=pd.read_parquet(path,columns=NYC_COLUMNS)
        # Normalize NaN to None; timestamps to stable ISO strings.
        source_rows=len(df)
        if source_rows<size: raise ValueError(f'dataset has {source_rows} rows, requested {size}; no replication allowed')
        indices=random.Random(seed).sample(range(source_rows),size)
        rows=[]
        for item in df.iloc[indices].to_dict(orient='records'):
            rows.append({k:None if pd.isna(v) else v.isoformat() if hasattr(v,'isoformat') else v for k,v in item.items()})
    elif kind=='nslkdd':
        import csv
        rows=[]
        with path.open(newline='',encoding='utf-8') as f:
            for line in csv.reader(f):
                if len(line)!=43: raise ValueError('KDDTrain+ must contain exactly 43 fields')
                r=dict(zip(NSL_COLUMNS,line))
                for k in ('duration','src_bytes','dst_bytes'): r[k]=int(r[k])
                rows.append(r)
    else: raise ValueError('dataset must be nyc or nslkdd')
    if kind=='nyc':
        selected=rows
    elif len(rows)<size: raise ValueError(f'dataset has {len(rows)} rows, requested {size}; no replication allowed')
    if kind!='nyc':
        source_rows=len(rows)
        indices=random.Random(seed).sample(range(source_rows),size)
        selected=[rows[i] for i in indices]
    provenance={'kind':kind,'source_file':str(path.resolve()),'sha256':sha256_file(path),'source_rows':source_rows,'sample_rows':size,'seed':seed,'replacement':False,'indices_sha256':hashlib.sha256(json.dumps(indices,separators=(',',':')).encode()).hexdigest()}
    return selected,provenance

def synthetic(size=12,seed=2024):
    rng=random.Random(seed)
    return [{'fare_amount':None if i%7==0 else str(rng.randint(-1000,5000)/100),
             'trip_distance':str(rng.randint(0,2000)/100),'tip_amount':None if i%5==0 else str(rng.randint(-100,1000)/100),
             'research_canary':f'PPBENCH_CANARY_{i:08d}_SENSITIVE','payment_type':i%2,'VendorID':i%3,'tpep_pickup_datetime':f'2024-01-01T00:00:{i%60:02d}',
             'tpep_dropoff_datetime':f'2024-01-01T00:30:{i%60:02d}','PULocationID':i%263,'DOLocationID':(i+1)%263} for i in range(size)]
