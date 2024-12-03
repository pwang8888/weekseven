from web3 import Web3
from web3.middleware import geth_poa_middleware 
import json
import sys
from pathlib import Path

source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"

def connectTo(chain):
    if chain == 'avax':
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"  # AVAX C-chain testnet
    elif chain == 'bsc':
        api_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"  # BSC testnet
    else:
        print(f"Invalid chain: {chain}")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)  # Add middleware for POA
    return w3

def getContractInfo(chain):
    """
    Load the contract_info file into a dictionary.
    """
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open('r') as f:
            contracts = json.load(f)
    except Exception as e:
        print("Failed to read contract info")
        print("Please contact your instructor")
        print(e)
        sys.exit(1)

    return contracts[chain]

def send_transaction(web3, contract_function, args, private_key):
    """
    Sends a transaction to the blockchain.
    """
    try:
        account = web3.eth.account.from_key(private_key)
        nonce = web3.eth.get_transaction_count(account.address)
        gas_price = web3.eth.gas_price
        tx = contract_function(*args).build_transaction({
            'chainId': web3.eth.chain_id,
            'gas': 300000,
            'gasPrice': gas_price,
            'nonce': nonce
        })
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction successful: {tx_receipt.transactionHash.hex()}")
    except Exception as e:
        print(f"Transaction failed: {str(e)}")
        raise

def scanBlocks(chain):
    """
    Scan the last 5 blocks of the source and destination chains for events.
    """
    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return

    if chain == 'source':
        web3 = connectTo('avax')
        contract_info = getContractInfo('source')
        event_name = "Deposit"
        target_chain = 'bsc'
        target_function = "wrap"
    elif chain == 'destination':
        web3 = connectTo('bsc')
        contract_info = getContractInfo('destination')
        event_name = "Unwrap"
        target_chain = 'avax'
        target_function = "withdraw"

    contract = web3.eth.contract(address=contract_info['address'], abi=contract_info['abi'])
    latest_block = web3.eth.block_number
    start_block = max(latest_block - 5, 0)
    print(f"Scanning blocks {start_block} to {latest_block} on {chain} chain.")

    event_filter = getattr(contract.events, event_name).create_filter(fromBlock=start_block, toBlock=latest_block)
    events = event_filter.get_all_entries()

    for event in events:
        token = event.args.get('token')
        recipient = event.args.get('recipient')
        amount = event.args.get('amount')
        print(f"Detected {event_name}: Token={token}, Recipient={recipient}, Amount={amount}")

        target_web3 = connectTo(target_chain)
        target_info = getContractInfo(target_chain)
        target_contract = target_web3.eth.contract(address=target_info['address'], abi=target_info['abi'])

        try:
            send_transaction(
                target_web3,
                getattr(target_contract.functions, target_function),
                [token, recipient, amount],
                target_info["private_key"]
            )
        except Exception as e:
            print(f"Failed to execute {target_function} on {target_chain}: {str(e)}")

def main():
    """
    Main function to run the bridge script.
    """
    print("Scanning source chain for events...")
    scanBlocks('source')
    print("Scanning destination chain for events...")
    scanBlocks('destination')

if __name__ == "__main__":
    main()
