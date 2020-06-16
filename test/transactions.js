const Arweave = require('arweave/node');
const fs = require('fs');

const run_test = async function() {
    const wallet_path = '/home/mike/Documents/python/arkive/arkive/wallet/';
    const arweave = Arweave.init(arweave_config = {
        host: 'arweave.net',// Hostname or IP address for a Arweave node
        port: 443,           // Port, defaults to 1984
        protocol: 'https',  // Network protocol http or https, defaults to http
        timeout: 200000,     // Network request timeouts in milliseconds
        logging: true,     // Enable network request logging
    });

    let wallet_file = wallet_path;

    fs.readdirSync(wallet_path).forEach(file => {
        console.log(file);

        if(!file.endsWith('.json')) {
            return;
        }

        wallet_file += file;

        
    });

    const text = fs.readFileSync(wallet_file, 'utf8')
    const jwk = JSON.parse(text);


    // const data = fs.readFileSync("/home/mike/Documents/python/arweave-python-client/arweave-python-client/test/testfile0.bin");

    let transaction = await arweave.createTransaction({
        target: "OFD5dO06Wdurb4w5TTenzkw1PacATOP-6lAlfAuRZFk",
        quantity: arweave.ar.arToWinston('0.1')
    }, jwk);

    // transaction.addTag('key1', 'value1');
    // transaction.addTag('key2', 'value2');

    await arweave.transactions.sign(transaction, jwk)

    const result = await arweave.transactions.post(transaction);

    console.log(transaction.id);
    console.log(transaction.signature);
    console.log(transaction.data);
    console.log(transaction.data_root);
    console.log(transaction.data_size);
    
}

run_test();


