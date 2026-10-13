"""Bounded diagnostics, deliberately NOT NIST SP 800-22 or security proofs."""
import hashlib,json,random
from pathlib import Path
from .crypto import chaos_parameters,chaos_step,chaos_stream,chaos_xor
from .integrity import canonical

def hamming(a,b): return sum((x^y).bit_count() for x,y in zip(a,b))/(8*len(a))

def sensitivity(trials=16,length=256,seed=2024):
    rng=random.Random(seed); result=[]
    for i in range(trials):
        key=rng.randbytes(32); nonce=rng.randbytes(12)
        flipped=bytearray(key); flipped[i%32]^=1<<(i%8)
        fn=bytearray(nonce); fn[i%12]^=1<<(i%8)
        original=chaos_stream(key,nonce,length)
        result.append({'trial':i,'key_hamming_fraction':hamming(original,chaos_stream(bytes(flipped),nonce,length)),
                       'nonce_hamming_fraction':hamming(original,chaos_stream(key,bytes(fn),length))})
    return result

def cycle_scan(trials=16,steps=10000,seed=2024):
    rng=random.Random(seed); reports=[]
    for i in range(trials):
        x,rq=chaos_parameters(rng.randbytes(32),rng.randbytes(12)); seen={}; cycle=None
        for t in range(steps):
            if x in seen:
                cycle={'entry':seen[x],'period':t-seen[x]}; break
            seen[x]=t; x=chaos_step(x,rq)
        reports.append({'trial':i,'steps_checked':len(seen),'cycle':cycle})
    return reports

def nonce_reuse_demo():
    key=bytes(range(32)); nonce=bytes(range(12)); a=b'known plaintext 001'; b=b'other plaintext 002'
    ca=chaos_xor(a,key,nonce); cb=chaos_xor(b,key,nonce)
    return {'xor_leak_confirmed':bytes(x^y for x,y in zip(ca,cb))==bytes(x^y for x,y in zip(a,b)),
            'length':len(a),'interpretation':'same key/nonce exposes XOR; deliberate insecure reuse demonstration'}

def bounded_state_recovery(candidate_bits=12,known_bytes=8,predict_bytes=8):
    if not 1<=candidate_bits<=16: raise ValueError('bounded experiment limited to <=65536 candidates')
    key=bytes(range(32)); nonce=bytes(range(12)); x,rq=chaos_parameters(key,nonce)
    for _ in range(1024): x=chaos_step(x,rq)
    def output(state,length):
        out=[]
        for _ in range(length):
            state=chaos_step(state,rq); out.append((state>>32)&255)
        return bytes(out)
    truth=output(x,known_bytes+predict_bytes); prefix=x>>candidate_bits; matches=[]; predicted=0
    # Deliberately grants rq and high state bits: bounded known-plaintext search only.
    for low in range(1<<candidate_bits):
        candidate=(prefix<<candidate_bits)|low
        stream=output(candidate,known_bytes+predict_bytes)
        if stream[:known_bytes]==truth[:known_bytes]:
            matches.append(candidate); predicted+=int(stream[known_bytes:]==truth[known_bytes:])
    return {'candidate_bits':candidate_bits,'candidates':1<<candidate_bits,'known_state_high_bits':64-candidate_bits,
            'rq_given_to_attacker':True,'prefix_matches':len(matches),'holdout_predictions_matching':predicted,
            'true_state_in_matches':x in matches,'unique_state_recovered':len(matches)==1 and matches[0]==x,'interpretation':'multiple output-equivalent candidates do not constitute unique state recovery','known_bytes':known_bytes,'holdout_bytes':predict_bytes,
            'limitation':'privileged restricted search, NOT a full 64-bit state or key recovery attack; cannot establish resistance'}

def exposure_audit(bundle,canaries):
    serialized=canonical(bundle)
    findings={str(c):str(c).encode() in serialized for c in canaries}
    return {'scope':'protected JSON bytes only; no JVM/worker heap, OS swap, temp files or logs scanned',
            'canary_occurrences':findings,'proof':False,'warning':'absence of canaries is not proof of zero exposure; numeric strings can coincidentally occur in ciphertext representations'}

def security_report(output):
    report={'status':'bounded experimental diagnostics only','sensitivity':sensitivity(),'cycles':cycle_scan(),
            'nonce_reuse':nonce_reuse_demo(),'state_recovery':bounded_state_recovery(),
            'nist_sp800_22':{'status':'pending external full-suite execution','not_substituted_by_homegrown_tests':True}}
    Path(output).write_text(json.dumps(report,indent=2),encoding='utf-8'); return report
