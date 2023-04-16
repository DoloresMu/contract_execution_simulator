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
        bscscan_api_key = ""

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



    def mock_call_contract_function(self, sender_address, value, function_name, *args, **kwargs):
        functions = [item for item in self.contract.abi if item["type"] == "function" and item["name"] == function_name]
        sender_address = self.web3.toChecksumAddress(sender_address)
        receiver_address = self.web3.toChecksumAddress(args[0])
        args_list = list(args)
        args_list[0] = self.web3.toChecksumAddress(args[0])
        args = tuple(args_list)

        if len(functions) == 0:
            print(f"No function found with the name `{function_name}`")
            return

        if len(functions) > 1:
            print(f"Found {len(functions)} function(s) with the name `{function_name}`: {[f['signature'] for f in functions]}")

        for function in functions:
            try:
                method = self.contract.functions.__getitem__(function['name'])

                initial_sender_balance = self.contract.functions.balanceOf(sender_address).call()
                initial_receiver_balance = self.contract.functions.balanceOf(receiver_address).call()

                function = self.contract.get_function_by_name(function_name)

                self.impersonate_account(sender_address)

                tx = function(*args).buildTransaction({
                    'from': sender_address,
                    'gas': 30000000,
                    'gasPrice': self.web3.toWei('5', 'gwei'),
                    'value': value
                })

                tx_hash = self.web3.eth.send_transaction(tx)

                self.stop_impersonating_account(sender_address)

                print(f"Function call result: {tx_hash}")

                final_sender_balance = self.contract.functions.balanceOf(sender_address).call()
                final_receiver_balance = self.contract.functions.balanceOf(receiver_address).call()

                sender_balance_change = final_sender_balance - initial_sender_balance
                receiver_balance_change = final_receiver_balance - initial_receiver_balance

                transaction_details = {
                    "function_name": function_name,
                    "sender_address": sender_address,
                    "args": args,
                    "kwargs": kwargs,
                }

                state_change_summary = {
                    "sender": {
                        "address": sender_address,
                        "initial_balance": initial_sender_balance,
                        "final_balance": final_sender_balance,
                        "balance_change": sender_balance_change
                    },
                    "receiver": {
                        "address": receiver_address,
                        "initial_balance": initial_receiver_balance,
                        "final_balance": final_receiver_balance,
                        "balance_change": receiver_balance_change
                    }
                }

                return transaction_details, state_change_summary

            except Exception as e:
                print(f"Function invocation failed: {e}")
                traceback.print_exc()
                return None, None

        return None, None


if __name__ == "__main__":
    #network.connect('ganache-fork')


    contract_address = "0xe9e7cea3dedca5984780bafc599bd69add087d56"
    mock_contract = Mock_Contract(contract_address)

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

