import json
import os
import requests
import logging
import hashlib
import arrow
import nacl.bindings
from jose import jwk
from jose.utils import base64url_encode, base64url_decode, base64
from jose.backends.cryptography_backend import CryptographyRSAKey
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
from Crypto.Hash import SHA256
from .utils import (
    winston_to_ar, 
    ar_to_winston, 
    owner_to_address,
    create_tag,
    encode_tag,
    decode_tag
)
from .deep_hash import deep_hash
from .merkle import compute_root_hash


logger = logging.getLogger(__name__)

TRANSACTION_DATA_LIMIT_IN_BYTES = 2000000

class Wallet(object):
    HASH = 'sha256'

    def __init__(self, jwk_file='jwk_file.json'):
        with open(jwk_file, 'r') as j_file:
            self.jwk_data = json.loads(j_file.read())
            self.jwk_data['p2s'] = ''
            self.jwk = jwk.construct(self.jwk_data, algorithm=jwk.ALGORITHMS.RS256)
            self.rsa = RSA.importKey(self.jwk.to_pem())
            
            self.owner = self.jwk_data.get('n')
            self.address = owner_to_address(self.owner)

        self.api_url = "https://arweave.net"
        self.balance = 0
        
    def get_balance(self):
        url = "{}/wallet/{}/balance".format(self.api_url, self.address)

        response = requests.get(url)

        if response.status_code == 200:
            self.balance = winston_to_ar(response.text)

        return self.balance  
    
    def sign(self, message):
        h = SHA256.new(message)
        signed_data = PKCS1_PSS.new(self.rsa).sign(h)      
        return signed_data
    
    def verify(self):
        pass 
    
    def get_last_transaction_id(self):
        url = "{}/tx_anchor".format(self.api_url)

        response = requests.get(url)

        if response.status_code == 200:
            self.last_tx = response.text
            
        return self.last_tx


class Transaction(object):
    def __init__(self, wallet, **kwargs):
        self.jwk_data = wallet.jwk_data
        self.jwk = jwk.construct(self.jwk_data, algorithm="RS256")
        self.wallet = wallet
        
        self.id = kwargs.get('id', '')
        self.last_tx = wallet.get_last_transaction_id()
        self.owner = self.jwk_data.get('n')
        self.tags = []
        self.quantity = kwargs.get('quantity', '0')

        self.format = kwargs.get('format', 2)
        
        data = kwargs.get('data', '')

        if type(data) is bytes:
            self.data = base64url_encode(data)
        else:
            self.data = base64url_encode(data.encode('ascii'))

        self.data_size = len(data)
        root_hash = compute_root_hash(data)
        self.data_root = base64url_encode(root_hash)
        self.data_tree = []

        self.target = kwargs.get('target', '')
        self.to = kwargs.get('to', '')
        
        self.api_url = "https://arweave.net"
        
        reward = kwargs.get('reward', None)
        if reward is not None:
            self.reward = reward  
        else:
            self.reward = self.get_reward(self.data)
            
        self.signature = ''
        self.status = None
        
    def get_reward(self, data, target_address=None):
        data_length = len(data)
        
        url = "{}/price/{}".format(self.api_url,data_length)
        
        if target_address:
            url = "{}/price/{}/{}".format(self.api_url, data_length, target_address)

        response = requests.get(url)

        if response.status_code == 200:
            reward = response.text
            
        return reward       
    
    def add_tag(self, name, value):
        tag = create_tag(name, value, self.format == 2)
        self.tags.append(tag)

    def encode_tags(self):
        tags = []
        for tag in self.tags:
            tags.append(encode_tag(tag))

        self.tags = tags
        
    def sign(self):
        data_to_sign = self.get_signature_data()
        
        raw_signature = self.wallet.sign(data_to_sign)
        
        self.signature = base64url_encode(raw_signature)
        
        self.id = base64url_encode(hashlib.sha256(raw_signature).digest())

        if type(self.id) == bytes:
            self.id = self.id.decode()
        
    def get_signature_data(self):
        if self.format == 1:
            tag_str = ""

            for tag in self.tags:
                name, value = decode_tag(tag)
                tag_str += "{}{}".format(name.decode(), value.decode())

            owner = base64url_decode(self.jwk_data['n'].encode())
            target = base64url_decode(self.target)
            data = base64url_decode(self.data)
            quantity = self.quantity.encode()
            reward = self.reward.encode()
            last_tx = base64url_decode(self.last_tx.encode())

            signature_data = owner + target + data + quantity + reward + last_tx + tag_str.encode()

        if self.format == 2:
            tag_list = [[tag['name'].encode(), tag['value'].encode()] for tag in self.tags]

            signature_data_list = [
                "2".encode(),
                base64url_decode(self.jwk_data['n'].encode()),
                base64url_decode(self.target),
                self.quantity.encode(),
                self.reward.encode(),
                base64url_decode(self.last_tx.encode()),
                tag_list,
                str(self.data_size).encode(),
                base64url_decode(self.data_root)]

            signature_data = deep_hash(signature_data_list)

        return signature_data
    
    def send(self):
        url = "{}/tx".format(self.api_url)

        response = requests.post(url, data=self.json_data)

        logger.error("{}\n\n{}".format(response.text, self.json_data))

        if response.status_code == 200:
            logger.debug("RESPONSE 200: {}".format(response.text))
        else:
            logger.error("{}\n\n{}".format(response.text, self.json_data))
            
        return self.last_tx    
    
    @property
    def json_data(self):
        data = {
                 'data': self.data.decode(),
                 'id': self.id.decode() if type(self.id) == bytes else self.id,
                 'last_tx': self.last_tx,
                 'owner': self.owner,
                 'quantity': self.quantity,
                 'reward': self.reward,
                 'signature': self.signature.decode(),
                 'tags': self.tags,
                 'target': self.target
                }

        if self.format == 2:
            self.encode_tags()
            data['tags'] = self.tags
            data['format'] = 2
            data['data_root'] = self.data_root.decode()
            data['data_size'] = str(self.data_size)
            data['data_tree'] = []

        jsons = json.dumps(data)
        
        return jsons.replace(' ','')
    
    def get_status(self):
        url = "{}/tx/{}/status".format(self.api_url, self.id)

        response = requests.get(url)

        if response.status_code == 200:
            self.status = json.loads(response.text)
        else:
            logger.error(response.text)  
            self.status = "PENDING"
            
        return self.status
    
    def get_transaction(self):
        url = "{}/tx/{}".format(self.api_url, self.id)

        response = requests.get(url)
        
        tx = None

        if response.status_code == 200:
            self.load_json(response.text)
        else:
            logger.error(response.text)    
            
        return tx
            
    def load_json(self, json_str):
        json_data = json.loads(json_str)
        
        self.data = json_data.get('data', '')
        self.last_tx = json_data.get('last_tx', '')
        self.owner = json_data.get('owner', '')
        self.quantity = json_data.get('quantity', '')
        self.reward = json_data.get('reward', '')
        self.signature = json_data.get('signature', '')
        self.tags = json_data.get('tags', '')
        self.target = json_data.get('target', '')
        self.data_size = json_data.get('data_size', '0')
        self.data_root = json_data.get('data_root', '')
        self.data_tree = json_data.get('data_tree', [])
        
        logger.debug(json_data)
        



