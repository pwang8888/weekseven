from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from web3.middleware import geth_poa_middleware #Necessary for POA chains
import json
import sys
from pathlib import Path

source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"

def connectTo(chain):
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet

    if chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet

    if chain in ['avax','bsc']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def getContractInfo(chain):
    """
        Load the contract_info file into a dictinary
        This function is used by the autograder and will likely be useful to you
    """
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open('r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( "Failed to read contract info" )
        print( "Please contact your instructor" )
        print( e )
        sys.exit(1)

    return contracts[chain]



def scanBlocks(chain):
    """
        chain - (string) should be either "source" or "destination"
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
        When Deposit events are found on the source chain, call the 'wrap' function the destination chain
        When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """

    if chain not in ['source','destination']:
        print( f"Invalid chain: {chain}" )
        return
    
        #YOUR CODE HERE
       # Determine chain connection and contract info
    if chain == "source":
        w3 = connectTo(source_chain)
        contract_info = getContractInfo("source")
        event_name = "Deposit"
    elif chain == "destination":
        w3 = connectTo(destination_chain)
        contract_info = getContractInfo("destination")
        event_name = "Unwrap"

    # Load the contract
    contract_address = contract_info["address"]
    contract_abi = contract_info["abi"]
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    # Scan the last 5 blocks
    end_block = w3.eth.get_block_number()
    start_block = max(0, end_block - 4)  # Ensure we don't go below block 0
    print(f"Scanning {chain} chain for {event_name} events from blocks {start_block} to {end_block}...")

    try:
        # Create filter for events
        event_filter = contract.events[event_name].create_filter(fromBlock=start_block, toBlock=end_block)
        events = event_filter.get_all_entries()

        for evt in events:
            print(f"Found {event_name} event: {evt}")

            # Extract event data
            token = evt.args["token"]
            recipient = evt.args["recipient"]
            amount = evt.args["amount"]

            # Handle Deposit or Unwrap events
            if chain == "source" and event_name == "Deposit":
                handle_wrap_on_destination(token, recipient, amount)
            elif chain == "destination" and event_name == "Unwrap":
                handle_withdraw_on_source(token, recipient, amount)

    except Exception as e:
        print(f"Error scanning blocks on {chain}: {e}")

def handle_wrap_on_destination(token, recipient, amount):
    """
    Handles a Deposit event by calling the wrap function on the destination chain.
    """
    print(f"Calling wrap on destination chain for token={token}, recipient={recipient}, amount={amount}...")
    try:
        destination_w3 = connectTo(destination_chain)
        destination_contract_info = getContractInfo("destination")
        destination_contract = destination_w3.eth.contract(
            address=destination_contract_info["address"], abi=destination_contract_info["abi"]
        )

        # Call the wrap function
        tx_hash = destination_contract.functions.wrap(token, recipient, amount).transact()
        print(f"wrap() transaction sent: {tx_hash.hex()}")
    except Exception as e:
        print(f"Error calling wrap on destination chain: {e}")

def handle_withdraw_on_source(token, recipient, amount):
    """
    Handles an Unwrap event by calling the withdraw function on the source chain.
    """
    print(f"Calling withdraw on source chain for token={token}, recipient={recipient}, amount={amount}...")
    try:
        source_w3 = connectTo(source_chain)
        source_contract_info = getContractInfo("source")
        source_contract = source_w3.eth.contract(
            address=source_contract_info["address"], abi=source_contract_info["abi"]
        )

        # Call the withdraw function
        tx_hash = source_contract.functions.withdraw(token, recipient, amount).transact()
        print(f"withdraw() transaction sent: {tx_hash.hex()}")
    except Exception as e:
        print(f"Error calling withdraw on source chain: {e}")

if __name__ == "__main__":
    # Scan blocks on the source chain
    scanBlocks("source")

    # Scan blocks on the destination chain
    scanBlocks("destination")

