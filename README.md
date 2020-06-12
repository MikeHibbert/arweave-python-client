# arweave-python-client
This client allows you to integrate your python apps with the Arweave network allowing you to got wallet operations and transactions

## Installing
To use the library simply install it:
```buildoutcfg
pip install arweave-python-client
```

## Using your wallet
Once installed you can import it and supply the wallet object with the path to your wallet JSON file:
```buildoutcfg
import arweave


wallet_file_path = "/some/folder/on/your/system"
wallet = arweave.Wallet(wallet_file_path)

balance =  wallet.get_balance()

last_transaction = wallet.get_last_transaction_id()
```

## Transactions
To send a transaction you will need to open your wallet, create a transaction object, sign the transaction and then finally post the transaction:
```buildoutcfg
import arweave


wallet_file_path = "/some/folder/on/your/system"
wallet = arweave.Wallet(wallet_file_path)

transaction = arweave.Transaction(wallet, quantity=0.3, to='<some wallet address')
transaction.sign()
transaction.send()
```

#####ATTENTION! quantity is in AR and is automatically converted to Winston before sending


To check the status of a transaction after sending:
```buildoutcfg
status = transaction.get_status()
```

To check the status much later you can store the ```transaction.id``` and reload it:
```buildoutcfg
transaction = Transaction(wallet, id='some id you stored')
status = transaction.get_status()
```

## Storing data
As you know Arweave allows you to permanently store data on the network and you can do this by supplying data to the transaction as a string object:
```buildoutcfg
wallet = Wallet(jwk_file)

with open('myfile.pdf', 'r') as mypdf:
    pdf_string_data = mypdf.read()
    
    transaction = Transaction(wallet, data=pdf_string_data)
    transaction.sign()
    transaction.send()
```

## Retrieving transactions/data
To get the information about a transaction you can create a transaction object with the ID of that transaction:
```
tx = Transaction(id=<your tx id>)
tx.get_transaction()
```

In addition you may want to get the data attached to this transaction once you've decided you need it:
```
tx.get_data()
print(tx.data) 
> "some data"
```

## Sending to a specific Node
You can specify a specific node by setting the api_url of the wallet/transaction object:
```
wallet = Wallet(jwk_file)
wallet.api_url = 'some specific node ip/address and port'

Or

transaction = Transaction(wallet, data=pdf_string_data)
transaction.api_url = 'some specific node ip/address and port'

```

## Arql
You can now perform searches using the arql method:
```buildoutcfg
import arweave

wallet_file_path = "/some/folder/on/your/system"
wallet = arweave.Wallet(wallet_file_path)

transaction_ids = aweave.arql(
    wallet, 
    {
        "op": "equals",
        "expr1": "from",
        "expr2": "Some owner address"
    })
```

Alternatively, you can use a the helper method arql_with_transaction_data() to get all transaction ids as well as all the data stored in the blockchain
```buildoutcfg
import arweave

wallet_file_path = "/some/folder/on/your/system"
wallet = arweave.Wallet(wallet_file_path)

transactions = aweave.arql_with_transaction_data(
    wallet, 
    {
        "op": "equals",
        "expr1": "from",
        "expr2": "Some owner address"
    })
```
