from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from web3.middleware import geth_poa_middleware
import json
import sys
from pathlib import Path

source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"


PRIVATE_KEY = "f447cac1243f3e6eaa439a774c3fd4203166ff2859b115d40670b2da163a018a"


def connectTo(chain):
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"  # AVAX C-chain testnet
    if chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"  # BSC testnet
    if chain in ['avax', 'bsc']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3


def getContractInfo(chain):
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open('r') as f:
            contracts = json.load(f)
    except Exception as e:
        print("Failed to read contract info")
        print(e)
        sys.exit(1)
    return contracts[chain]


def scanBlocks(chain):
    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return

    if chain == "source":
        w3 = connectTo(source_chain)
        contract_info = getContractInfo("source")
        event_name = "Deposit"
    elif chain == "destination":
        w3 = connectTo(destination_chain)
        contract_info = getContractInfo("destination")
        event_name = "Unwrap"

    contract = w3.eth.contract(address=contract_info["address"], abi=contract_info["abi"])
    end_block = w3.eth.block_number
    start_block = max(0, end_block - 4)  # Ensure we don't go below block 0

    print(f"Scanning {chain} chain for {event_name} events from blocks {start_block} to {end_block}...")

    try:
        event_filter = contract.events[event_name].create_filter(fromBlock=start_block, toBlock=end_block)
        events = event_filter.get_all_entries()

        for evt in events:
            print(f"Found {event_name} event: {evt}")
            token = evt.args["token"]
            recipient = evt.args["recipient"]
            amount = evt.args["amount"]

            if chain == "source" and event_name == "Deposit":
                handle_wrap_on_destination(w3, token, recipient, amount)
            elif chain == "destination" and event_name == "Unwrap":
                handle_withdraw_on_source(w3, token, recipient, amount)

    except Exception as e:
        print(f"Error scanning blocks on {chain}: {e}")


def handle_wrap_on_destination(w3, token, recipient, amount):
    print(f"Calling wrap on destination chain for token={token}, recipient={recipient}, amount={amount}...")
    try:
        destination_contract_info = getContractInfo("destination")
        destination_contract = w3.eth.contract(
            address=destination_contract_info["address"], abi=destination_contract_info["abi"]
        )
        account = w3.eth.account.from_key(PRIVATE_KEY)
        nonce = w3.eth.get_transaction_count(account.address)
        tx = destination_contract.functions.wrap(token, recipient, amount).build_transaction({
            "from": account.address,
            "gas": 500000,
            "gasPrice": w3.eth.gas_price,
            "nonce": nonce
        })
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"wrap() transaction sent: {tx_hash.hex()}")
    except Exception as e:
        print(f"Error calling wrap on destination chain: {e}")


def handle_withdraw_on_source(w3, token, recipient, amount):
    print(f"Calling withdraw on source chain for token={token}, recipient={recipient}, amount={amount}...")
    try:
        source_contract_info = getContractInfo("source")
        source_contract = w3.eth.contract(
            address=source_contract_info["address"], abi=source_contract_info["abi"]
        )
        account = w3.eth.account.from_key(PRIVATE_KEY)
        nonce = w3.eth.get_transaction_count(account.address)
        tx = source_contract.functions.withdraw(token, recipient, amount).build_transaction({
            "from": account.address,
            "gas": 500000,
            "gasPrice": w3.eth.gas_price,
            "nonce": nonce
        })
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"withdraw() transaction sent: {tx_hash.hex()}")
    except Exception as e:
        print(f"Error calling withdraw on source chain: {e}")


if __name__ == "__main__":
    scanBlocks("source")
    scanBlocks("destination")
