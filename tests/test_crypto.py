import unittest,math
from decimal import Decimal
from unittest.mock import patch
from ppbench.crypto import *

class CryptoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.sk=keygen(128,test_only=True)
    def test_signed_addition_and_randomness(self):
        pk=self.sk.public; a=pk.encrypt(-123);b=pk.encrypt(125)
        self.assertEqual(self.sk.decrypt(a*b%pk.n2),2)
        self.assertNotEqual(pk.encrypt(5),pk.encrypt(5))
        self.assertEqual(self.sk.decrypt(pk.encrypt(-123)),-123)
    def test_bounds_and_ciphertext(self):
        pk=self.sk.public
        with self.assertRaises(OverflowError):pk.encrypt(pk.signed_limit)
        with self.assertRaises(OverflowError):check_sum_bound(pk,pk.signed_limit//2,3)
        for c in (0,pk.n,pk.n2,-1):
            with self.assertRaises(ValueError):self.sk.decrypt(c)
        c=(1+pk.n*(pk.n//2))%pk.n2
        with self.assertRaises(OverflowError): self.sk.decrypt(c)
    def test_production_key_policy(self):
        with self.assertRaises(ValueError):keygen(128)
    def test_rounding_null_and_negative(self):
        self.assertEqual(encode('-1.235'),-124)
        self.assertEqual(encode('-1.225'),-122)
        self.assertIsNone(encode(None))
        self.assertEqual(decode(-124),Decimal('-1.24'))
        for v in ('NaN','Infinity'):
            with self.assertRaises(ValueError):encode(v)
    def test_chaos_exact_rational(self):
        key=bytes(32);nonce=bytes(12); x,rq=chaos_parameters(key,nonce)
        d=hashlib.sha256(key+nonce).digest(); u=int.from_bytes(d[8:12],'big')
        from fractions import Fraction
        self.assertEqual(rq,math.floor((Fraction(39,10)+Fraction(99,1000)*u/(1<<32))*(1<<32)))
        self.assertEqual(chaos_step(x,rq),(rq*x*((1<<64)-x))//(1<<96))
        payload=b'negative -1.25 and null'; ct=chaos_xor(payload,key,nonce)
        self.assertEqual(chaos_xor(ct,key,nonce),payload)
    def test_zero_state_retry(self):
        class Fake:
            def __init__(self,d):self.d=d
            def digest(self):return self.d
        with patch('ppbench.crypto.hashlib.sha256',side_effect=[Fake(bytes(32)),Fake(b'\x00'*7+b'\x01'+b'\x00'*24)]) as m:
            x,r=chaos_parameters(bytes(32),bytes(12));self.assertEqual(x,1)
            self.assertEqual(m.call_args.args[0][-4:],b'\x00\x00\x00\x01')

class AESGCMTests(unittest.TestCase):
    def setUp(self):
        try: import cryptography
        except ImportError:self.skipTest('cryptography missing')
    def test_aad_tamper_and_nonce_reuse(self):
        c=RecordCipher(bytes(32)); nonce,ct=c.encrypt('record1',b'payload',bytes(12))
        self.assertEqual(c.decrypt('record1',nonce,ct),b'payload')
        with self.assertRaises(Exception):c.decrypt('record2',nonce,ct)
        changed=bytearray.fromhex(ct);changed[0]^=1
        with self.assertRaises(Exception):c.decrypt('record1',nonce,changed.hex())
        with self.assertRaises(ValueError):c.encrypt('record3',b'payload',bytes(12))
