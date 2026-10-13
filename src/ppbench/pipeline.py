import json,secrets
from decimal import Decimal
from .crypto import encode,decode,chaos_xor,check_sum_bound,RecordCipher
from .integrity import canonical,sign_manifest,verify_manifest
from .model import CONFIGS

def protect(rows,config,keys,numeric,visible,scale=100,partition_size=1000,owner='research',version=1):
    if config not in CONFIGS: raise ValueError('unknown configuration')
    cipher=RecordCipher(keys.aes); out=[]; chaos_nonces=set()
    bounds={f:max((abs(encode(r.get(f),scale)) for r in rows if r.get(f) is not None),default=0) for f in numeric}
    for f in numeric: check_sum_bound(keys.paillier.public,bounds[f],len(rows))
    for i,row in enumerate(rows):
        rid=str(i)
        if config=='PLAIN': entry={'id':rid,'plain':row}
        elif config=='AES-DEC':
            nonce,ct=cipher.encrypt(rid,canonical(row)); entry={'id':rid,'nonce':nonce,'aes':ct}
        else:
            entry={'id':rid,'visible':{f:row.get(f) for f in visible},
                   'numbers':{f:None if row.get(f) is None else str(keys.paillier.public.encrypt(encode(row[f],scale))) for f in numeric}}
            sensitive={k:v for k,v in row.items() if k not in numeric and k not in visible}
            if config=='H-GCM':
                nonce,ct=cipher.encrypt(rid,canonical(sensitive)); entry.update(nonce=nonce,aes=ct)
            else:
                while True:
                    nonce=secrets.token_bytes(12)
                    if nonce not in chaos_nonces: break
                chaos_nonces.add(nonce)
                entry.update(nonce=nonce.hex(),chaos=chaos_xor(canonical(sensitive),keys.chaos,nonce).hex())
        out.append(entry)
    partitions=[out[i:i+partition_size] for i in range(0,len(out),partition_size)]
    meta={'configuration':config,'numeric':list(numeric),'visible':list(visible),'scale':scale,
          'row_count':len(rows),'bounds':bounds,'owner':owner,'version':version}
    # Authenticate metadata as its own canonical partition: configuration and bounds cannot be altered.
    manifest=sign_manifest([ [meta] ]+partitions,keys.manifest,owner,version)
    return {'metadata':meta,'partitions':partitions,'manifest':manifest}

def verify(bundle,keys,owner='research',version=1):
    return verify_manifest([[bundle['metadata']]]+bundle['partitions'],bundle['manifest'],keys.manifest,owner,version)

def materialize(bundle,keys):
    config=bundle['metadata']['configuration']; rows=[]; cipher=RecordCipher(keys.aes)
    for partition in bundle['partitions']:
        for r in partition:
            if config=='PLAIN': row=r['plain']
            elif config=='AES-DEC': row=json.loads(cipher.decrypt(r['id'],r['nonce'],r['aes']))
            else:
                if config=='H-GCM': raw=cipher.decrypt(r['id'],r['nonce'],r['aes'])
                else: raw=chaos_xor(bytes.fromhex(r['chaos']),keys.chaos,bytes.fromhex(r['nonce']))
                row=json.loads(raw); row.update(r['visible'])
                row.update({f:None if c is None else str(decode(keys.paillier.decrypt(int(c)),bundle['metadata']['scale'])) for f,c in r['numbers'].items()})
            rows.append(row)
    return rows

def _plain_partial(row,group,numeric,scale):
    vals={f:encode(row.get(f),scale) for f in numeric}
    return ('ALL' if group is None else canonical(row.get(group)).decode(),(1,{f:(0 if v is None else v, int(v is not None)) for f,v in vals.items()}))

def _hybrid_partial(row,group,numeric,n2):
    return ('ALL' if group is None else canonical(row['visible'].get(group)).decode(),(1,{f:(1 if row['numbers'][f] is None else int(row['numbers'][f]),int(row['numbers'][f] is not None)) for f in numeric}))

def _aes_partial(row,aes_key,group,numeric,scale):
    plain=json.loads(RecordCipher(aes_key).decrypt(row['id'],row['nonce'],row['aes']))
    return _plain_partial(plain,group,numeric,scale)

def _merge(a,b,hybrid,n2):
    return (a[0]+b[0],{f:(((a[1][f][0]*b[1][f][0])%n2 if hybrid else a[1][f][0]+b[1][f][0]),a[1][f][1]+b[1][f][1]) for f in a[1]})

def query(bundle,keys,group,backend='python-smoke',spark=None):
    meta=bundle['metadata']; config=meta['configuration']; numeric=meta['numeric']; hybrid=config.startswith('H-')
    if hybrid and group is not None and group not in meta['visible']: raise ValueError('hybrid grouping requires visible field')
    for f in numeric: check_sum_bound(keys.paillier.public,meta['bounds'][f],meta['row_count'])
    n2=keys.paillier.public.n2; scale=meta['scale']
    rows=([r for p in bundle['partitions'] for r in p] if hybrid or (backend=='spark' and config=='AES-DEC') else materialize(bundle,keys))
    if backend=='spark':
        if spark is None: raise ValueError('SparkSession required')
        rdd=spark.sparkContext.parallelize(rows)
        if hybrid: mapped=rdd.map(lambda r:_hybrid_partial(r,group,numeric,n2))
        elif config=='AES-DEC':
            aes_key=keys.aes  # Baseline deliberately sends the AES key to workers.
            mapped=rdd.map(lambda r:_aes_partial(r,aes_key,group,numeric,scale))
        else: mapped=rdd.map(lambda r:_plain_partial(r,group,numeric,scale))
        # Spark workers receive only public modulus and ciphertexts in hybrid mode.
        result=mapped.reduceByKey(lambda a,b:_merge(a,b,hybrid,n2)).collect()
        return dict(result)
    if backend!='python-smoke': raise ValueError('no silent Spark fallback')
    result={}
    for row in rows:
        k,v=(_hybrid_partial(row,group,numeric,n2) if hybrid else _plain_partial(row,group,numeric,scale))
        result[k]=v if k not in result else _merge(result[k],v,hybrid,n2)
    return result

def finalize(raw,bundle,keys):
    hybrid=bundle['metadata']['configuration'].startswith('H-'); scale=bundle['metadata']['scale']; result={}
    for group,(count,vals) in raw.items():
        stats={}
        for f,(total,nonnull) in vals.items():
            value=decode(keys.paillier.decrypt(total) if hybrid else total,scale)
            stats[f]={'sum':None if not nonnull else str(value),'count_nonnull':nonnull,'avg':None if not nonnull else str(value/Decimal(nonnull))}
        result[group]={'count_star':count,'fields':stats}
    return result
