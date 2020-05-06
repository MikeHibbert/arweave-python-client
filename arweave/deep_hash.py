import hashlib
from jose.utils import base64url_encode, base64url_decode, base64
from jose.backends.cryptography_backend import CryptographyRSAKey
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
from Crypto.Hash import SHA384


def deep_hash(data):
    if type(data) == list:
        tag = b"list" + str(len(data)).encode()

        return deep_hash_chunks(data, hashlib.sha384(tag).digest())

    else:
        tag = b"blob" + str(len(data)).encode()

    tagged_hash = hashlib.sha384(tag).digest() + hashlib.sha384(data).digest()

    return hashlib.sha384(tagged_hash).digest()


def deep_hash_chunks(chunks, acc):
    if len(chunks) < 1:
        return acc

    hash_pair = acc + deep_hash(chunks[0])

    new_acc = hashlib.sha384(hash_pair).digest()

    return deep_hash_chunks(chunks[1:], new_acc)