from arweave import Wallet
import arweave
import responses

wallet = Wallet("test_jwk_file.json")

api_url = arweave.arweave_lib.API_URL


@responses.activate
def test_get_balance():
    # register successful response
    mock_balance = "12345678"
    mock_url = '{}/wallet/{}/balance'.format(api_url, wallet.address)
    responses.add(responses.GET, mock_url, body=mock_balance, status=200)
    # execute test against mocked response
    balance = wallet.get_balance()
    assert balance == mock_balance


@responses.activate
def test_get_last_transaction_id():
    # register successful response
    mock_tx_id = "12345678"
    mock_url = '{}/tx_anchor'.format(api_url)
    responses.add(responses.GET, mock_url, body=mock_tx_id, status=200)
    last_tx_id = wallet.get_last_transaction_id()

    assert last_tx_id == mock_tx_id
    assert wallet.last_tx == mock_tx_id


if __name__ == "__main__":
    test_get_balance()
    test_get_last_transaction_id()
