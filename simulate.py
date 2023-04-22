import json
import requests
import traceback
from pathlib import Path
from web3 import Web3
from eth_account import Account
from web3.middleware import geth_poa_middleware
from brownie import accounts, network, config


class MockContract:
    contract = None
    alice = None
    bob = None
    eva = None
    mave = None
    web3 = None

    def make_fork_filter_middleware(self, block_number: int) -> callable:
        def middleware(make_request, web3):
            def _filter_new_blocks(method, params):
                if method == "eth_newBlockFilter":
                    params = list(params)
                    filter_params: FilterParams = params[0]
                    filter_params.from_block = block_number
                    params[0] = filter_params
                return make_request(method, params)

            return _filter_new_blocks

        return middleware

    def function_exists(self, function_name):
        for item in self.contract.abi:
            if item['type'] == 'function' and item['name'] == function_name:
                return True
        return False

    def get_impersonated_account_nonce(self, address):
        return self.web3.eth.getTransactionCount(address)

    def impersonate_account(self, address):
        self.web3.provider.make_request("hardhat_impersonateAccount", [address])

    def stop_impersonating_account(self, address):
        self.web3.provider.make_request("hardhat_stopImpersonatingAccount", [address])

    def __init__(self, contract_address):
        contract_address = Web3.toChecksumAddress(contract_address)
        bscscan_api_key = "Y7XSHW2HQYG56EZWKNR39QCPEZ3KCI5B7E"

        output_file = Path("./contracts/contract_abi.json")

        url = f"https://api.bscscan.com/api?module=contract&action=getabi&address={contract_address}&apikey={bscscan_api_key}"
        response = requests.get(url)
        data = response.json()

        contract_abi = json.loads(data['result'])

        with output_file.open(mode="w") as f:
            json.dump(contract_abi, f)

        self.web3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        self.contract = self.web3.eth.contract(address=contract_address, abi=contract_abi)

        alice_private_key = Account.create().privateKey
        self.alice = accounts.add(alice_private_key)
        print(self.alice)

        pre_funded_account = accounts[0]
        initial_alice_balance = self.web3.toWei(1, "ether")
        gas_price = self.web3.eth.gasPrice

        print(self.alice)

        bob_private_key = Account.create().privateKey
        self.bob = accounts.add(bob_private_key)
        print(self.bob)


    def reset_hardhat_network(self):
        current_block_number = self.web3.eth.blockNumber
        self.web3.provider.make_request("hardhat_reset", [{"forking": {"jsonRpcUrl": "http://127.0.0.1:8545", "blockNumber": current_block_number}}])


    

    def mock_call_contract_function(self, mode, sender_address, value, function_name,  *args, **kwargs):
        #self.reset_hardhat_network()
        functions = [item for item in self.contract.abi if item["type"] == "function" and item["name"] == function_name]
        sender_address = self.web3.toChecksumAddress(sender_address)
        receiver_address = self.web3.toChecksumAddress(args[0])
        args_list = list(args)
        args_list[0] = self.web3.toChecksumAddress(args[0])
        args = tuple(args_list)



        
        if mode == "force":
            pre_funded_account = accounts[0]
            desired_balance = self.web3.toWei(1, "ether") 
            gas_price = self.web3.eth.gasPrice  # Get the current gas price

            transaction = {
                'to': sender_address,
                'value': desired_balance,
                'gas': 21000,
                'gasPrice': gas_price,
                'chainId': self.web3.eth.chainId
            }

            self.impersonate_account(pre_funded_account.address)
            tx_hash = self.web3.eth.send_transaction(transaction)
            receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

            self.stop_impersonating_account(pre_funded_account.address)


        def get_all_view_function_values(contract, address):
            values = {}
            for item in contract.abi:
                if item['type'] == 'function' and item['stateMutability'] == 'view':
                    try:
                        method = contract.functions.__getitem__(item['name'])
                        values[item['name']] = method(address).call()
                    except Exception as e:
                        print(f"Error calling view function '{item['name']}': {e}")
            return values

        if len(functions) == 0:
            print(f"No function found with the name `{function_name}`")
            return

        if len(functions) > 1:
            print(f"Found {len(functions)} function(s) with the name `{function_name}`: {[f['signature'] for f in functions]}")

        for function in functions:
            try:
                method = self.contract.functions.__getitem__(function['name'])

                
                initial_sender_view_values = get_all_view_function_values(self.contract, sender_address)
                initial_receiver_view_values = get_all_view_function_values(self.contract, receiver_address)
                try:
                    initial_sender_balance = self.contract.functions.balanceOf(sender_address).call()
                    initial_receiver_balance = self.contract.functions.balanceOf(receiver_address).call()
                except Exception as e:
                    traceback.print_exc()
                    initial_sender_balance = 0
                    initial_receiver_balance = 0


                function = self.contract.get_function_by_name(function_name)


                self.impersonate_account(sender_address)

                tx = function(*args).buildTransaction({
                    'from': sender_address,
                    'gas': 30000000,
                    'gasPrice': self.web3.toWei('5', 'gwei'),
                    'value': value
                })

                tx_hash = self.web3.eth.send_transaction(tx)
                receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

                

                internal_transactions = []

                for log in receipt['logs']:
                    try:
                        # Find the matching event in the contract ABI
                        event_abi = None
                        for item in self.contract.abi:
                            if item['type'] == 'event' and log['topics'][0] == self.web3.sha3(text=item['signature']).hex():
                                event_abi = item
                                break

                        if event_abi is not None:
                            # Use the event ABI to decode the log
                            event_data = self.web3.eth.abi.decodeLog(event_abi['inputs'], log['data'], log['topics'][1:])
                            event_args = dict(zip([input['name'] for input in event_abi['inputs']], event_data))

                            internal_transactions.append({
                                "event_name": event_abi['name'],
                                "args": event_args,
                            })

                    except Exception as e:
                        print(f"Error decoding log: {e}")



                self.stop_impersonating_account(sender_address)

                print(f"Function call result: {tx_hash}")

                final_sender_view_values = get_all_view_function_values(self.contract, sender_address)
                final_receiver_view_values = get_all_view_function_values(self.contract, receiver_address)

                try:
                    final_sender_balance = self.contract.functions.balanceOf(sender_address).call()
                    final_receiver_balance = self.contract.functions.balanceOf(receiver_address).call()
                except:
                    print()
                    final_sender_balance = 0
                    final_receiver_balance = 0

                transaction_details = {
                    "function_name": function_name,
                    "sender_address": sender_address,
                    "args": args,
                    "kwargs": kwargs,
                }

                state_change_summary = {
                    "statechange":{
                        "sender": {
                            "totalBalance": final_sender_balance - initial_sender_balance,
                        },
                        "receiver": {
                            "totalBalance": final_receiver_balance - initial_receiver_balance,
                        }
                    },
                    "details":{
                        "sender": {
                            "address": sender_address,
                            "initial_state": initial_sender_view_values,
                        "final_state": final_sender_view_values
                    },
                        "receiver": {
                            "address": receiver_address,
                            "initial_state": initial_receiver_view_values,
                        "final_state": final_receiver_view_values,
                    },
                      'internal_transactions': internal_transactions
                    }

                }
                    

                return transaction_details, state_change_summary, None

            except Exception as e:
                print(f"Function invocation failed: {e}")
                traceback.print_exc()
                return None, None, str(e)

        return None, None, "function not found in contract"


    def mock_transaction(self, mode, sender_address, value, data:str):
        #self.reset_hardhat_network()
        functions = [item for item in self.contract.abi if item["type"] == "function" and item["name"] == function_name]
        sender_address = self.web3.toChecksumAddress(sender_address)
        receiver_address = self.web3.toChecksumAddress(args[0])
        args_list = list(args)
        args_list[0] = self.web3.toChecksumAddress(args[0])
        args = tuple(args_list)

        
        if mode == "force":
            pre_funded_account = accounts[0]
            desired_balance = self.web3.toWei(1, "ether") 
            gas_price = self.web3.eth.gasPrice  # Get the current gas price

            transaction = {
                'to': sender_address,
                'value': desired_balance,
                'gas': 21000,
                'gasPrice': gas_price,
                'chainId': self.web3.eth.chainId
            }

            self.impersonate_account(pre_funded_account.address)
            tx_hash = self.web3.eth.send_transaction(transaction)
            receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

            self.stop_impersonating_account(pre_funded_account.address)


        def get_all_view_function_values(contract, address):
            values = {}
            for item in contract.abi:
                if item['type'] == 'function' and item['stateMutability'] == 'view':
                    try:
                        method = contract.functions.__getitem__(item['name'])
                        values[item['name']] = method(address).call()
                    except Exception as e:
                        print(f"Error calling view function '{item['name']}': {e}")
            return values


        initial_sender_view_values = get_all_view_function_values(self.contract, sender_address)
        initial_receiver_view_values = get_all_view_function_values(self.contract, receiver_address)
        try:
            initial_sender_balance = self.contract.functions.balanceOf(sender_address).call()
            initial_receiver_balance = self.contract.functions.balanceOf(receiver_address).call()
        except Exception as e:
            traceback.print_exc()
            initial_sender_balance = 0
            initial_receiver_balance = 0

        self.impersonate_account(sender_address)

        tx = {
            "from": sender_address,
            "to": self.contract.address,
            "gas": 30000000,
            "value": 0,
            "data": data,
            "gasPrice": self.web3.toWei('5', 'gwei')
        }
        tx_hash = self.web3.eth.send_transaction(tx)
        receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

                

        internal_transactions = []

        for log in receipt['logs']:
            try:
                # Find the matching event in the contract ABI
                event_abi = None
                for item in self.contract.abi:
                    if item['type'] == 'event' and log['topics'][0] == self.web3.sha3(text=item['signature']).hex():
                        event_abi = item
                        break

                if event_abi is not None:
                    # Use the event ABI to decode the log
                    event_data = self.web3.eth.abi.decodeLog(event_abi['inputs'], log['data'], log['topics'][1:])
                    event_args = dict(zip([input['name'] for input in event_abi['inputs']], event_data))

                    internal_transactions.append({
                        "event_name": event_abi['name'],
                        "args": event_args,
                    })

            except Exception as e:
                print(f"Error decoding log: {e}")



        self.stop_impersonating_account(sender_address)

        print(f"Function call result: {tx_hash}")

        final_sender_view_values = get_all_view_function_values(self.contract, sender_address)
        final_receiver_view_values = get_all_view_function_values(self.contract, receiver_address)

        try:
            final_sender_balance = self.contract.functions.balanceOf(sender_address).call()
            final_receiver_balance = self.contract.functions.balanceOf(receiver_address).call()
        except:
            print()
            final_sender_balance = 0
            final_receiver_balance = 0

        transaction_details = {
            "function_name": function_name,
            "sender_address": sender_address,
            "args": args,
            "kwargs": kwargs,
        }

        state_change_summary = {
            "statechange":{
                "sender": {
                    "totalBalance": final_sender_balance - initial_sender_balance,
                },
                "receiver": {
                    "totalBalance": final_receiver_balance - initial_receiver_balance,
                }
            },
            "details":{
                "sender": {
                    "address": sender_address,
                    "initial_state": initial_sender_view_values,
                "final_state": final_sender_view_values
            },
                "receiver": {
                    "address": receiver_address,
                    "initial_state": initial_receiver_view_values,
                "final_state": final_receiver_view_values,
            },
                'internal_transactions': internal_transactions
            }

        }
            

        return transaction_details, state_change_summary, None





if __name__ == "__main__":
    #network.connect('ganache-fork')


    contract_address = "0xe9e7cea3dedca5984780bafc599bd69add087d56"
    mock_contract = MockContract(contract_address)

    mock_sender = '0x3f5617de2221828110d42588e11c0aade1baa6a4'
    mock_sender = Web3.toChecksumAddress(mock_sender)
    # Impersonate the target address
    #impersonated_account = accounts.at(mock_sender, force=True)
    #accounts.add(impersonated_account.privateKey) # Add this line



    pre_funded_account = accounts[0]  # The first pre-funded account in the development environment
    initial_balance = mock_contract.web3.toWei(1, "ether")  # Set the desired balance for the impersonated account in Ether
    gas_price = mock_contract.web3.eth.gasPrice  # Get the current gas price
    #pre_funded_account.transfer(impersonated_account, initial_balance, gas_price=gas_price)

    mock_receiver = '0xd73bb365c572656aae5662e9409fc563f629f112'
    mock_amount = 149999
    print(mock_contract.mock_call_contract_function(mock_sender , 0,  'transfer', Web3.toChecksumAddress(mock_receiver), mock_amount))

