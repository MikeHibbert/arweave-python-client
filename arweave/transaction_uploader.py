import json
import arrow
import random
import time
import requests
import logging
from jose.utils import base64url_encode, base64url_decode
from .arweave_lib import Transaction
from .utils import *
from .merkle import validate_path, CHUNK_SIZE
from .arweave_lib import API_URL

from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)

logger = logging.getLogger(__name__)

MAX_CHUNKS_IN_BODY = 1

FATAL_CHUNK_UPLOAD_ERRORS = ['invalid_json', 'chunk_too_big', 'data_path_too_big', 'offset_too_big', 'data_size_too_big', 'chunk_proof_ratio_not_attractive', 'invalid_proof']

ERROR_DELAY = 1000 * 40


class TransactionUploaderException(Exception):
    pass


class TransactionUploader:
    def __init__(self, *args, **kwargs):
        self.chunk_index = kwargs.get('chunk_index', 0)
        self.tx_posted = kwargs.get('tx_posted', False)
        self.transaction = kwargs['transaction']
        self.last_request_time_end = kwargs.get('last_request_time_end', 0)
        self.last_response_status = kwargs.get('last_response_status', 0)
        self.last_response_error = kwargs.get('last_response_error', '')
        self.transaction.data = b''  # zero out data for serialization
        self.file_handler = kwargs['file_handler']
        self.total_errors = 0
        self.data = None

    @property
    def is_complete(self):
        return self.tx_posted and self.chunk_index == len(self.transaction.chunks.get("chunks"))

    @property
    def total_chunks(self):
        return len(self.transaction.chunks.get("chunks"))

    @property
    def uploaded_chunks(self):
        return self.chunk_index

    @property
    def pct_complete(self):
        return int("{}".format(self.uploaded_chunks / self.total_chunks * 100).split('.')[0])

    def to_json(self):
        data = {
            "chunkIndex": self.chunk_index,
            "transaction": self.transaction.to_dict(),
            "lastRequestTimeEnd": self.last_request_time_end,
            "lastResponseStatus": self.last_response_status,
            "lastResponseError": self.last_response_error,
            "lastResponseError": self.tx_posted
        }

        return json.dumps(data)

    def load_from_json(self, data):
        if type(data) == str:
            data = json.loads(data)

        self.chunk_index = data['chunkIndex']
        self.transaction = Transaction.from_serialized_transaction(data['transaction'])
        self.last_request_time_end = arrow.now(data['lastRequestTimeEnd']).timestamp
        self.last_response_status = data['lastResponseStatus']
        self.last_response_error = data['lastResponseError']
        self.tx_posted = data['lastResponseError']

    def upload_chunk(self):
        if self.is_complete:
            raise TransactionUploaderException("Upload is already complete")

        if self.last_response_error != '':
            self.total_errors += 1
        else:
            self.total_errors = 0

        if self.total_errors == 100:
            raise TransactionUploaderException(
                "Unable to complete upload: {}: {}".format(self.last_response_status, self.last_response_error)
            )

        delay = 0

        if self.last_response_error != '':
            delay = max(
                (self.last_request_time_end + ERROR_DELAY) - arrow.now().timestamp,
                ERROR_DELAY
            )

        if delay > 0:
            delay = delay - (delay * random.random() * 0.3)
            time.sleep(delay)

        self.last_response_error = ''

        if not self.tx_posted:
            self.post_transaction()

        chunk = self.transaction.get_chunk(self.chunk_index)

        chunk_ok = validate_path(
            self.transaction.chunks.get('data_root'),
            int(chunk.get('offset')),
            0,
            int(chunk.get('data_size')),
            base64url_decode(chunk.get('data_path'))
        )

        if not chunk_ok:
            raise TransactionUploaderException("Unable to validate chunk {}".format(self.chunk_index))

        self.data = chunk['chunk']  # = self.get_chunk_data(self.chunk_index)
        chunk['data_path'] = chunk['data_path'].decode()
        chunk['chunk'] = chunk['chunk'].decode()

        url = "{}/chunk".format(self.transaction.api_url)

        headers = {'Content-Type': 'application/json', 'Accept': 'text/plain'}

        response = requests.post(url, data=json.dumps(chunk), headers=headers)

        # logger.error("{}\n\n{}".format(response.text, self.transaction.json_data))

        if response.status_code == 200:
            logger.debug("RESPONSE 200: {}".format(response.text))
        else:
            logger.error("{}".format(response.text))

            return {"status": -1, "data": {"error": response.text}}

        self.last_request_time_end = arrow.now().timestamp
        self.last_response_status = response.status_code

        if self.last_response_status == 200:
            self.chunk_index += 1
        else:
            self.last_response_error = json.loads(response.text)

            if self.last_response_error.error in FATAL_CHUNK_UPLOAD_ERRORS:
                raise TransactionUploaderException(
                    "Fatal error uploading chunk {}: {}".format(self.chunk_index, self.last_response_error.error)
                )

    def get_chunk_data(self, chunk_index):
        self.file_handler.seek(chunk_index * CHUNK_SIZE)
        data = self.file_handler.read(CHUNK_SIZE)

        return base64url_encode(data)

    def post_transaction(self):
        upload_in_body = self.total_chunks <= MAX_CHUNKS_IN_BODY

        if upload_in_body:
            url = "{}/tx".format(self.transaction.api_url)
            headers = {'Content-Type': 'application/json', 'Accept': 'text/plain'}

            self.transaction.data = self.data

            json_data = self.transaction.json_data
            response = requests.post(url, data=json_data, headers=headers)

            self.last_request_time_end = arrow.now().timestamp
            self.last_response_status = response.status_code
            self.transaction.data = b''

            if 200 <= response.status_code < 300:
                logger.debug("RESPONSE 200: {}".format(response.text))
                self.tx_posted = True
                self.chunk_index = MAX_CHUNKS_IN_BODY
                return
            else:
                logger.error("{}\n\n{}".format(response.text, self.json_data))

                self.last_response_error = json.loads(response.text)

                raise TransactionUploaderException(
                    "Unable to upload transaction {}, {}".format(response.status_code, self.last_response_error)
                )

        url = "{}/tx".format(self.transaction.api_url)
        headers = {'Content-Type': 'application/json', 'Accept': 'text/plain'}

        self.transaction.data = b''

        json_data = self.transaction.json_data
        response = requests.post(url, data=json_data, headers=headers)

        self.last_request_time_end = arrow.now().timestamp
        self.last_response_status = response.status_code
        self.transaction.data = b''

        if not (200 <= response.status_code < 300):
            self.last_response_error = json.loads(response.text)

            raise TransactionUploaderException(
                "Unable to upload transaction {}, {}".format(response.status_code, self.last_response_error)
            )

        self.tx_posted = True


class TransactionDownloaderException(Exception):
    pass


def get_transaction_offset(tx_id):
    url = "{}/tx/{}/offset".format(API_URL, tx_id)

    response = requests.get(url)
    response_json = json.loads(response.text)

    if response.status_code == 200:
        return int(response_json.get("data"))
    else:
        raise TransactionDownloaderException(
            "Unable to get transaction offset: {}".format(response_json.get("error"))
        )

def get_chunk(offset):
    url = "{}/chunk/{}".format(API_URL, offset)

    response = requests.get(url)
    response_json = json.loads(response.text)

    if response.status_code == 200:
        return response_json.get("data")
    else:
        raise TransactionDownloaderException(
            "Unable to get chunk: {}".format(response_json.get("error"))
        )


def get_chunk_data(offset):
    chunk = get_chunk(offset)
    buf = base64url_decode(chunk.get('chunk'))
    return buf


def first_chunk_offset(offset_response):
    return int(offset_response.get('offset')) - int(offset_response.get('size')) + 1


def download_chunked_data(tx_id, file_handler=None):
    offset_response = get_transaction_offset(tx_id)

    size = int(offset_response.get('size'))
    end_offset = int(offset_response.get('offset'))
    start_offset = end_offset - size + 1

    byte_offset = 0

    if file_handler is None:
        data = bytearray(length=size)

    while start_offset + byte_offset < end_offset:
        chunk_data = get_chunk_data(start_offset + byte_offset)

        if file_handler is None:
            data[byte_offset:] = byte(chunk_data)
        else:
            file_handler.seek(byte_offset)
            file_handler.write(chunk_data)

        



def from_serialized(self, file_handler, json_str):
    if json_str is None:
        raise TransactionUploaderException("Serialized object does not match expected format")

    serialized = json.loads(json_str)

    if type(serialized.chunk_index) != int or type(serialized.transaction) != object:
        raise TransactionUploaderException("Serialized object does not match expected format")

    upload = TransactionUploader(
        file_handler=file_handler,
        transaction=Transaction(
            transaction=serialized.transaction
        )
    )


def from_transaction_id(file_handler, transaction_str, wallet, api_url=API_URL):
    tx = json.loads(transaction_str)

    url = "{}/tx/{}".format(api_url, tx.get('id'))

    headers = {'Content-Type': 'application/json', 'Accept': 'text/plain'}

    response = requests.get(url, headers=headers)

    logger.error("{}".format(response.text))

    if response.status_code == 200:
        logger.debug("RESPONSE 200: {}".format(response.text))
    else:
        raise TransactionUploaderException("Tx {} not found: {} {}".format(
            tx.get('id'),
            response.status_code,
            response.text)
        )

    serialized = TransactionUploader(
        tx_posted=True,
        chunk_index=0,
        last_response_error='',
        last_request_time_end=0,
        last_response_status=0,
        file_handler=file_handler,
        transaction=Transaction(
            wallet,
            transaction=response.text
        )
    )

    return serialized


def get_uploader(upload, file_handler):
    uploader = None
    if type(upload) == Transaction:
        uploader = TransactionUploader(file_handler=file_handler, transaction=upload)
    else:
        if type(upload) == str:
            upload = from_transaction_id(file_handler, upload)

        uploader = TransactionUploader(file_handler=file_handler, transaction=upload)

    return uploader
