"""Integer-only Paillier and explicitly experimental logistic-map stream masking."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib, hmac, math, secrets

U64 = 1 << 64

def _prime(bits):
    while True:
        n = secrets.randbits(bits) | (1 << (bits-1)) | 1
        if any(n % p == 0 for p in (3,5,7,11,13,17,19,23,29,31,37)):
            continue
        d, s = n-1, 0
        while d % 2 == 0:
            s += 1; d //= 2
        # 64 independent strong probable-prime rounds; not a certified prime.
        for _ in range(64):
            a = 2 + secrets.randbelow(n-3)
            x = pow(a, d, n)
            if x in (1, n-1): continue
            for __ in range(s-1):
                x = pow(x, 2, n)
                if x == n-1: break
            else: break
        else: return n

@dataclass(frozen=True)
class PublicKey:
    n: int
    @property
    def n2(self): return self.n * self.n
    @property
    def signed_limit(self): return self.n // 3
    def encrypt(self, value):
        if not isinstance(value, int): raise TypeError('raw integer required')
        if abs(value) >= self.signed_limit: raise OverflowError('plaintext outside signed range')
        while True:
            r = 1 + secrets.randbelow(self.n-1)
            if math.gcd(r, self.n) == 1: break
        return ((1 + self.n * (value % self.n)) * pow(r, self.n, self.n2)) % self.n2
    def check_ciphertext(self, c):
        if not isinstance(c,int) or not 0 < c < self.n2 or math.gcd(c,self.n) != 1:
            raise ValueError('invalid Paillier ciphertext')

@dataclass(frozen=True)
class PrivateKey:
    public: PublicKey
    lam: int
    mu: int
    def decrypt(self, ciphertext):
        self.public.check_ciphertext(ciphertext)
        n = self.public.n
        v = ((pow(ciphertext,self.lam,n*n)-1)//n * self.mu) % n
        if v < n//3: return v
        if v > n - n//3: return v-n
        raise OverflowError('signed decoding overflow sentinel')

def keygen(bits=2048, *, test_only=False):
    if bits < 2048 and not test_only: raise ValueError('research key size must be >=2048 bits')
    if bits < 32 or bits % 2: raise ValueError('even key size >=32 required')
    while True:
        p,q = _prime(bits//2), _prime(bits//2)
        if p == q: continue
        n=p*q
        if n.bit_length() != bits: continue
        lam=math.lcm(p-1,q-1)
        if math.gcd(lam,n)==1: return PrivateKey(PublicKey(n),lam,pow(lam,-1,n))

def encode(value, scale=100):
    if value is None: return None
    x=Decimal(str(value))
    if not x.is_finite(): raise ValueError('nonfinite number')
    if not isinstance(scale,int) or scale <= 0: raise ValueError('positive integer scale required')
    return int((x*scale).quantize(Decimal('1'),rounding=ROUND_HALF_EVEN))

def decode(value, scale=100): return Decimal(value)/Decimal(scale)

def check_sum_bound(public, max_abs, count):
    # Mandatory preflight; modular wraparound can otherwise evade sentinel detection.
    if max_abs*count >= public.signed_limit: raise OverflowError('aggregate may wrap signed range')

def chaos_parameters(key, nonce):
    if len(key)!=32 or len(nonce)!=12: raise ValueError('32-byte key and 12-byte nonce required')
    seed=hashlib.sha256(key+nonce).digest()
    x=int.from_bytes(seed[:8],'big'); counter=0
    while x==0:
        counter+=1
        seed=hashlib.sha256(key+nonce+counter.to_bytes(4,'big')).digest()
        x=int.from_bytes(seed[:8],'big')
    u=int.from_bytes(seed[8:12],'big')
    # floor((39/10 + (99/1000)*u/2^32)*2^32), exact rational.
    rq=(3900*(1<<32)+99*u)//1000
    return x,rq

def chaos_step(x,rq): return (rq*x*(U64-x)) >> 96

def chaos_stream(key,nonce,length):
    x,rq=chaos_parameters(key,nonce)
    for _ in range(1024): x=chaos_step(x,rq)
    out=bytearray()
    for _ in range(length):
        x=chaos_step(x,rq); out.append((x>>32)&255)
    return bytes(out)

def chaos_xor(data,key,nonce):
    return bytes(a^b for a,b in zip(data,chaos_stream(key,nonce,len(data))))

class RecordCipher:
    """AES-GCM binds record identifier as AAD. Nonce tracking is per key object."""
    def __init__(self,key):
        if len(key)!=32: raise ValueError('AES-256 key required')
        self.key=key; self.used=set()
    def encrypt(self,record_id,data,nonce=None):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce=secrets.token_bytes(12) if nonce is None else nonce
        if len(nonce)!=12: raise ValueError('96-bit nonce required')
        if nonce in self.used: raise ValueError('nonce reuse under same key')
        self.used.add(nonce)
        return nonce.hex(),AESGCM(self.key).encrypt(nonce,data,str(record_id).encode()).hex()
    def decrypt(self,record_id,nonce,ciphertext):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        return AESGCM(self.key).decrypt(bytes.fromhex(nonce),bytes.fromhex(ciphertext),str(record_id).encode())
