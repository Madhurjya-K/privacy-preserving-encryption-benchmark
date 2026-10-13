from dataclasses import dataclass

CONFIGS=('PLAIN','AES-DEC','H-CHAOS','H-GCM')
@dataclass
class Keys:
    paillier: object
    aes: bytes
    chaos: bytes
    manifest: bytes

# All fields not listed as visible or numeric are sensitive payload fields.
NYC_NUMERIC=('fare_amount','trip_distance','tip_amount')
NYC_VISIBLE=('payment_type','VendorID')
NSL_NUMERIC=('duration','src_bytes','dst_bytes')
NSL_VISIBLE=('protocol_type',)
