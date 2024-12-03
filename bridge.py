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
      
    if chain == 'source':
        web3 = connectTo('avax')
        contract_info = getContractInfo('source')
    elif chain == 'destination':
        web3 = connectTo('bsc')
        contract_info = getContractInfo('destination')

    contract = web3.eth.contract(address=contract_info['address'], abi=contract_info['abi'])
    
    # Define block range
    latest_block = web3.eth.block_number
    start_block = max(latest_block - 5, 0)
    end_block = latest_block

    print(f"Scanning blocks {start_block} to {end_block} on {chain} chain.")

    # Define the event to scan for
    if chain == 'source':
        event_name = "Deposit"
        action = "wrap"
    elif chain == 'destination':
        event_name = "Unwrap"
        action = "withdraw"

    event_filter = getattr(contract.events, event_name).create_filter(fromBlock=start_block, toBlock=end_block)
    events = event_filter.get_all_entries()

    for evt in events:
        token = evt.args['token']
        recipient = evt.args['recipient']
        amount = evt.args['amount']

        print(f"Event detected: {event_name} - Token: {token}, Recipient: {recipient}, Amount: {amount}")

        # Perform the cross-chain action
        if chain == 'source':
            print(f"Calling {action} on destination chain for token {token}, recipient {recipient}, amount {amount}")
            destination_web3 = connectTo('bsc')
            destination_info = getContractInfo('destination')
            destination_contract = destination_web3.eth.contract(address=destination_info['address'], abi=destination_info['abi'])
            send_transaction(
                destination_web3,
                destination_contract.functions.wrap,
                [token, recipient, amount],
                destination_info['private_key']
            )
        elif chain == 'destination':
            print(f"Calling {action} on source chain for token {token}, recipient {recipient}, amount {amount}")
            source_web3 = connectTo('avax')
            source_info = getContractInfo('source')
            source_contract = source_web3.eth.contract(address=source_info['address'], abi=source_info['abi'])
            send_transaction(
                source_web3,
                source_contract.functions.withdraw,
                [token, recipient, amount],
                source_info['private_key']
            )
