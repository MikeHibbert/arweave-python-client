const Arweave = require('arweave/node');
const fs = require('fs');

const run_test = async function() {
    const wallet_path = '/home/mike/Documents/python/arkive/arkive/wallet/arweave-keyfile-h-Bgr13OWUOkRGWrnMT0LuUKfJhRss5pfTdxHmNcXyw.json';
    const arweave = Arweave.init(arweave_config = {
        host: 'arweave.net',// Hostname or IP address for a Arweave node
        port: 443,           // Port, defaults to 1984
        protocol: 'https',  // Network protocol http or https, defaults to http
        timeout: 200000,     // Network request timeouts in milliseconds
        logging: false,     // Enable network request logging
    });

    const text = fs.readFileSync(wallet_path, 'utf8')
    const jwk = JSON.parse(text);

    let transaction = await arweave.createTransaction({
        data: 'test'
    }, jwk);

    transaction.addTag('key1', 'value1');
    transaction.addTag('key2', 'value2');

    arweave.transactions.sign(transaction, jwk)

    const result = await arweave.transactions.post(transaction);

    console.log(transaction.id);
    console.log(transaction.signature);
    console.log(transaction.data);
    console.log(transaction.data_root);
    console.log(transaction.data_size);
}

run_test();


