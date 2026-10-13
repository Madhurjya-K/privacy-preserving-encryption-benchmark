"""Authenticated canonical-partition manifest; trusted version state is external."""
import hashlib,hmac,json

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()

def partition_hash(rows):
    # Sorting intentionally makes permutation inside a partition unobservable.
    return hashlib.sha256(b'['+b','.join(sorted(canonical(r) for r in rows))+b']').hexdigest()

def sign_manifest(partitions,key,owner,version):
    if not owner or not isinstance(version,int) or version<1: raise ValueError('owner and positive version required')
    body={'format':1,'owner':owner,'version':version,'partitions':[
        {'index':i,'count':len(rows),'sha256':partition_hash(rows)} for i,rows in enumerate(partitions)]}
    return {'body':body,'hmac_sha256':hmac.new(key,canonical(body),hashlib.sha256).hexdigest()}

def verify_manifest(partitions,manifest,key,owner,current_version):
    body=manifest['body']
    expected=hmac.new(key,canonical(body),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,manifest['hmac_sha256']): raise ValueError('manifest authentication failed')
    if body['owner']!=owner or body['version']!=current_version: raise ValueError('owner/version mismatch or rollback')
    calculated=sign_manifest(partitions,key,owner,current_version)
    if calculated['body']!=body: raise ValueError('partition corruption, insertion, deletion, duplication or movement')
    return True
