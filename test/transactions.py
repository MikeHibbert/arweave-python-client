import os
import logging
from arweave.arweave_lib import Wallet, Transaction, arql, arql_with_transaction_data

logger = logging.getLogger(__name__)


def run_test(jwk_file):
    wallet = Wallet(jwk_file)

    DATA = b'dGVzdA'
    DATA_ROOT = b'uwdqwpnoHTe237EIEIOizSYku8wkiVZJY-E6cv33wt4'

    balance = wallet.get_balance()

    logger.debug(balance)
    data = "test"
    with open("testfile0.bin", "rb") as pdf_file:
        data = pdf_file.read()

    tx = Transaction(wallet=wallet, data=data)

    tx.add_tag('key1', 'value1');
    tx.add_tag('key2', 'value2');

    tx.sign()

    tx.send()

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

    transaction_ids = arql(
        wallet,
        {
            "op": "equals",
            "expr1": "from",
            "expr2": "OFD5dO06Wdurb4w5TTenzkw1PacATOP-6lAlfAuRZFk"
        }
    )

    if len(transaction_ids) == 0:
        raise Exception("AQRL search failed to find any transactions")

    transactions = arql_with_transaction_data(
        wallet,
        {
            "op": "equals",
            "expr1": "from",
            "expr2": "OFD5dO06Wdurb4w5TTenzkw1PacATOP-6lAlfAuRZFk"
        }
    )

    if len(transactions) == 0:
        raise Exception("AQRL search failed to find any transactions")




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