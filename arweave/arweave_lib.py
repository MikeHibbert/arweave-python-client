import json
import os
import io
import requests
import logging
import hashlib
import psutil
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
from .merkle import compute_root_hash, generate_transaction_chunks

logger = logging.getLogger(__name__)

TRANSACTION_DATA_LIMIT_IN_BYTES = 2000000
API_URL = "https://arweave.net"

class ArweaveTransactionException(Exception):
    pass


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

        self.api_url = API_URL
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
        else:
            raise ArweaveTransactionException(response.text)
            
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
        self.format = kwargs.get('format', 2)

        self.api_url = API_URL
        self.chunks = None
        
        data = kwargs.get('data', '')
        self.data_size = len(data)

        if type(data) is bytes:
            self.data = base64url_encode(data)
        else:
            self.data = base64url_encode(data.encode('ascii'))

        self.file_handler = kwargs.get('file_handler', None)
        if self.file_handler:
            self.uses_uploader = True
            self.data_size = os.stat(kwargs['file_path']).st_size
        else:
            self.uses_uploader = False

        if kwargs.get('transaction'):
            self.from_serialized_transaction(kwargs.get('transaction'))
        else:
            self.data_root = ""

            self.data_tree = []

            self.target = kwargs.get('target', '')
            self.to = kwargs.get('to', '')

            if self.target == '' and self.to != '':
                self.target = self.to

            self.quantity = kwargs.get('quantity', '0')
            if float(self.quantity) > 0:
                if self.target == '':
                    raise ArweaveTransactionException("Unable to send {} AR without specifying a target address".format(self.quantity))

                # convert to winston
                self.quantity = ar_to_winston(float(self.quantity))

            reward = kwargs.get('reward', None)
            if reward is not None:
                self.reward = reward

            self.signature = ''
            self.status = None

    def from_serialized_transaction(self, transaction_json):
        if type(transaction_json) == str:
            self.load_json(transaction_json)
        else:
            raise ArweaveTransactionException("Please supply a string containing json to initialize a serialized transaction")
        
    def get_reward(self, data_size, target_address=None):

        url = "{}/price/{}".format(self.api_url,data_size)
        
        if target_address:
            url = "{}/price/{}/{}".format(self.api_url, data_size, target_address)

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
        self.reward = self.get_reward(self.data_size, target_address=self.target if len(self.target) > 0 else None)

        if self.data_size > 0 and self.data_root == "":
            if type(self.data) == str:
                root_hash = compute_root_hash(io.StringIO(self.data))

            if type(self.data) == bytes:
                root_hash = compute_root_hash(io.BytesIO(self.data))

            self.data_root = base64url_encode(root_hash)

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
            if self.uses_uploader:
                self.prepare_chunks()

            tag_list = [[tag['name'].encode(), tag['value'].encode()] for tag in self.tags]

            signature_data_list = [
                "2".encode(),
                base64url_decode(self.jwk_data['n'].encode()),
                base64url_decode(self.target.encode()),
                str(self.quantity).encode(),
                self.reward.encode(),
                base64url_decode(self.last_tx.encode()),
                tag_list,
                str(self.data_size).encode(),
                base64url_decode(self.data_root)]

            signature_data = deep_hash(signature_data_list)

        return signature_data
    
    def send(self):
        url = "{}/tx".format(self.api_url)

        headers = {'Content-Type': 'application/json', 'Accept': 'text/plain'}

        json_data = self.json_data
        response = requests.post(url, data=json_data, headers=headers)

        logger.error("{}\n\n{}".format(response.text, self.json_data))

        if response.status_code == 200:
            logger.debug("RESPONSE 200: {}".format(response.text))
        else:
            logger.error("{}\n\n{}".format(response.text, self.json_data))
            
        return self.last_tx

    def to_dict(self):
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
            if len(self.data_root) > 0:
                data['data_root'] = self.data_root.decode()
            else:
                data['data_root'] = ""
            data['data_size'] = str(self.data_size)
            data['data_tree'] = []

        return data

    @property
    def json_data(self):
        data = self.to_dict()

        json_str = json.dumps(data)

        logger.error(json_str)
        
        return json_str.replace(' ', '')
    
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

    def get_price(self):
        u = "{}/price/{}".format(self.api_url, self.data_size)

        response = requests.get(url)

        if response.status_code == 200:
            return winston_to_ar(int(response.text))
        else:
            logger.error(response.text)

    def get_data(self):
        url = "{}/{}/".format(self.api_url, self.id)

        response = requests.get(url)

        if response.status_code == 200:
            self.data = response.text
        else:
            logger.error(response.text)

            raise ArweaveTransactionException(
                response.text
            )

    def load_json(self, json_str):
        json_data = json.loads(json_str)
        
        self.data = json_data.get('data', '')
        self.last_tx = json_data.get('last_tx', '')
        self.owner = json_data.get('owner', '')
        self.quantity = json_data.get('quantity', '')
        self.reward = json_data.get('reward', '')
        self.signature = json_data.get('signature', '')
        self.tags = [decode_tag(tag) for tag in json_data.get('tags', [])]
        self.target = json_data.get('target', '')
        self.data_size = json_data.get('data_size', '0')
        self.data_root = json_data.get('data_root', '')
        self.data_tree = json_data.get('data_tree', [])
        
        logger.debug(json_data)

    def prepare_chunks(self):
        if not self.chunks:
            self.chunks = generate_transaction_chunks(self.file_handler)
            self.data_root = base64url_encode(self.chunks.get('data_root'))

        if not self.chunks:
            self.chunks = {
                "chunks": [],
                "data_root": b'',
                "proof": []
            }

            self.data_root = ''

    def get_chunk(self, idx):
        if self.chunks is None:
            raise ArweaveTransactionException("Chunks have not been prepared")

        proof = self.chunks.get('proofs')[idx]
        chunk = self.chunks.get('chunks')[idx]

        self.file_handler.seek(chunk.min_byte_range)

        chunk_data = self.file_handler.read(chunk.data_size)

        return {
            "data_root": self.data_root.decode(),
            "data_size": str(self.data_size),
            "data_path": base64url_encode(proof.proof),
            "offset": str(proof.offset),
            "chunk": base64url_encode(chunk_data)
        }


def arql(wallet, query):
    """
    Creat your query like so:
    query = {
        "op": "and",
          "expr1": {
            "op": "equals",
            "expr1": "from",
            "expr2": "hnRI7JoN2vpv__w90o4MC_ybE9fse6SUemwQeY8hFxM"
          },
          "expr2": {
            "op": "or",
            "expr1": {
              "op": "equals",
              "expr1": "type",
              "expr2": "post"
            },
            "expr2": {
              "op": "equals",
              "expr1": "type",
              "expr2": "comment"
            }
          }
    :param wallet:
    :param query:
    :return list of Transaction instances:
    """

    data = json.dumps(query)
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    response = requests.post("{}/arql".format(API_URL), data=data, headers=headers)

    if response.status_code == 200:
        transaction_ids = json.loads(response.text)

        return transaction_ids

    return None


def arql_with_transaction_data(wallet, query):
    """
    Creat your query like so:
    query = {
        "op": "and",
          "expr1": {
            "op": "equals",
            "expr1": "from",
            "expr2": "hnRI7JoN2vpv__w90o4MC_ybE9fse6SUemwQeY8hFxM"
          },
          "expr2": {
            "op": "or",
            "expr1": {
              "op": "equals",
              "expr1": "type",
              "expr2": "post"
            },
            "expr2": {
              "op": "equals",
              "expr1": "type",
              "expr2": "comment"
            }
          }
    :param wallet:
    :param query:
    :return list of Transaction instances:
    """

    transaction_ids = arql(wallet, query)
    if transaction_ids:
        transactions = []
        for transaction_id in transaction_ids:
            tx = Transaction(wallet, id=transaction_id)
            tx.get_transaction()
            tx.get_data()

            transactions.append(tx)

    return None




