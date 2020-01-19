# arweave-python-client
This client allows you to integrate your python apps with the Arweave network allowing you to got wallet operations and transactions

## Installing
To use the library simply install it:
```buildoutcfg
pip install arweave-python-client
```

##Using your wallet
Once installed you can import it and supply the wallet object with the path to your wallet JSON file:
```buildoutcfg
import arweave


wallet_file_path = "/some/folder/on/your/system"
wallet = arewave.Wallet(wallet_file_path)

balance =  wallet.get_balance()

last_transaction = wallet.get_last_transaction_id()
```

##Transactions
To send a transaction you will need to open your wallet, create a transaction object, sign the transaction and then finally post the transaction:
```buildoutcfg
import arweave


wallet_file_path = "/some/folder/on/your/system"
wallet = arewave.Wallet(wallet_file_path)

transaction = Transaction(wallet, quantity=0.3, to='<some wallet address')
transaction.sign(wallet)
transaction.send()
```

To check the status of a transaction after sending:
```buildoutcfg
status = transaction.get_status()
```

To check the status much later you can store the ```transaction.id``` and reload it:
```buildoutcfg
transaction = Transaction(wallet, id='some id you stored')
status = transaction.get_status()
```

##Storing data
As you know Arweave allows you to permanently store data on the network and you can do this by supplying data to the transaction as a string object:
```buildoutcfg
wallet = Wallet(jwk_file)

with open('myfile.pdf', 'r') as mypdf:
    pdf_string_data = mypdf.read()
    
    transaction = Transaction(wallet, data=pdf_string_data)
    transaction.sign()
    transaction.send()
```

