"""Load and enforce the exact preregistered v1 protocol, rather than guessing defaults."""
import hashlib,json
from pathlib import Path
EXPECTED={'version':1,'authors':['Madhurjya Kakati','Gracy Sonwan'],'configurations':['PLAIN','AES-DEC','H-CHAOS','H-GCM'],'sizes':[10000,50000,100000,500000],'repeats':10,'warmups':1,'seed':2024,'paillier_bits':2048,'scale':100,'partition_size':1000,'backend':'spark','nyc_release':'yellow_tripdata_2024-01.parquet','nsl_release':'KDDTrain+.txt'}

def load_protocol(path):
    path=Path(path);raw=path.read_bytes();obj=json.loads(raw)
    for key,expected in EXPECTED.items():
        if key not in obj or obj[key]!=expected:raise ValueError(f'frozen protocol mismatch for {key}: expected {expected!r}')
    unknown=set(obj)-set(EXPECTED)-{'note','nsl_size_limit'}
    if unknown:raise ValueError(f'unknown protocol fields: {sorted(unknown)}')
    return obj,{'protocol_path':str(path.resolve()),'protocol_sha256':hashlib.sha256(raw).hexdigest(),'version':obj['version']}

def validate_selection(protocol,dataset,size):
    if dataset not in ('nyc','nslkdd') or size not in protocol['sizes']:raise ValueError('dataset/size outside frozen protocol')
    if dataset=='nslkdd' and size==500000:raise ValueError('KDDTrain+ has 125973 records; 500000 without replacement is unavailable')
