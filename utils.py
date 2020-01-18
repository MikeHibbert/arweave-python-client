import hashlib
from jose import jwk
from jose.utils import base64url_encode, base64url_decode, base64


def create_tag(name, value):
    b64name = base64url_encode(name.encode('ascii')).decode()
    b64value = base64url_encode(value.encode('ascii')).decode()
    
    return {"name": b64name, "value":b64value}

def decode_tag(tag):
    name = base64url_decode(tag['name'].encode())
    value = base64url_decode(tag['value'].encode())
    
    return name, value
    
def owner_to_address(owner):
    result = base64url_encode(hashlib.sha256(base64url_decode(owner.encode('ascii'))).digest()).decode()

    return result

def winston_to_ar(winston_str):
    length = len(winston_str)
    
    if length > 12:
        past_twelve = length - 12
        winston_str = "{}.{}".format(winston_str[0:past_twelve], winston_str[-12:])
    else:
        lessthan_twelve = 12 - length
        winston_str = "0.{}{}".format(winston_str,"0" * lessthan_twelve)
        
    return float(winston_str)

def ar_to_winston(ar_amount):
    ar_str = "{:.12f}".format(ar_amount)
    return ar_str.replace('.','')