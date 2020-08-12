import os
import logging
from arweave.arweave_lib import Wallet, Transaction, arql, arql_with_transaction_data
from arweave.transaction_uploader import get_uploader, from_transaction_id

logger = logging.getLogger(__name__)


def run_test(jwk_file):
    wallet = Wallet(jwk_file)

    DATA = b'dGVzdA'
    DATA_ROOT = b'uwdqwpnoHTe237EIEIOizSYku8wkiVZJY-E6cv33wt4'

    balance = wallet.get_balance()

    logger.debug(balance)
    data = "test"

    ubuntu_iso_tx = 'Vw5mrDkj39JZSpDjM8FiJHsMnUf_EXeQh9XYo7GJstI'

    file_path = "/home/mike/Downloads/ubuntu-18.04.4-desktop-amd64.iso"
    # with open(file_path, "rb", buffering=0) as file_handler:
    #     tx = Transaction(wallet, id=ubuntu_iso_tx,file_handler=file_handler, file_path=file_path)
    #     tx.get_transaction()
    #     # tx.add_tag('Content-Type', 'application/pdf')
    #     tx.sign()
    #
    #     logger.error("{} chunks".format(len(tx.chunks['chunks'])))
    #
    #     uploader = get_uploader(tx, file_handler)
    #
    #     while not uploader.is_complete:
    #         uploader.upload_chunk()
    #         logger.info("{}% complete, {}/{}".format(
    #             uploader.pct_complete, uploader.uploaded_chunks, uploader.total_chunks
    #         ))
    #
    #     logger.info("{} uploaded successfully".format(tx.id))
    #
    # tx_ids = arql(wallet, {
    #     "op": "and",
    #     "expr1": {
    #         "op": "equals",
    #         "expr1": "from",
    #         "expr2": wallet.address
    #     },
    #     "expr2": {
    #         "op": "equals",
    #         "expr1": "Content-Type",
    #         "expr2": "application/pdf"
    #     }
    # })
    #
    # logger.error(tx_ids)
    #
    # for tx_id in tx_ids:
    #     tx = Transaction(wallet, id=tx_id)
    #
    #     tx.get_transaction()
    #
    #     logger.error("got {}".format(tx_id))
    #
    #     # tx.get_data()

    tx = Transaction(wallet, data=b'HELLO TEST')

    # tx.api_url = 'http://188.166.200.45:1984'
    tx.add_tag('key1', 'value1');
    tx.add_tag('key2', 'value2');

    tx.sign()

    tx.send()
    #
    logger.info(tx.id)
    logger.info(tx.data_root)

    # if tx.data != DATA:
    #     raise Exception("Data does not match expected result!")
    #
    # if tx.data_root != DATA_ROOT:
    #     raise Exception("Data root does not match expected result!")

    # tx = Transaction(wallet, id='HMDsP8HmP4KOsSYcKvFXXkj8hax-YD53tQC24VamgLo')
    #
    # tx.get_transaction()
    #
    # tx.get_data()
    #
    # logger.info(tx.data)
    # logger.info(tx.data_root)

    # if tx.data != DATA:
    #     raise Exception("Data does not match expected result!")
    #
    # if tx.data_root != DATA_ROOT:
    #     raise Exception("Data root does not match expected result!")

    # transaction_ids = arql(
    #     wallet,
    #     {
    #         "op": "equals",
    #         "expr1": "from",
    #         "expr2": "OFD5dO06Wdurb4w5TTenzkw1PacATOP-6lAlfAuRZFk"
    #     }
    # )
    #
    # if len(transaction_ids) == 0:
    #     raise Exception("AQRL search failed to find any transactions")
    #
    # transactions = arql_with_transaction_data(
    #     wallet,
    #     {
    #         "op": "equals",
    #         "expr1": "from",
    #         "expr2": "OFD5dO06Wdurb4w5TTenzkw1PacATOP-6lAlfAuRZFk"
    #     }
    # )
    #
    # if len(transactions) == 0:
    #     raise Exception("AQRL search failed to find any transactions")




if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    from os.path import isfile, join
    from os import listdir

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



    wallet_path = '/home/mike/Documents/python/arkive/arkive/wallet'  # os.path.join(BASE_DIR, 'arkive', 'wallet')

    files = [f for f in listdir(wallet_path) if isfile(join(wallet_path, f))]

    if len(files) > 0:
        filename = files[0]
    else:
        raise FileNotFoundError("Unable to load a wallet JSON file from wallet/ ")

    run_test(join(wallet_path, filename))