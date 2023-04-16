# Contract Execution Simulator

This project is a Python-based contract execution simulator that interacts with a local fork of the Binance Smart Chain (BSC). It utilizes the Hardhat development environment, Brownie, and Web3.py to interact with and simulate contract executions on the BSC.

## Directory Structure
```
.
├── LICENSE
├── brownie-config.yaml
├── contracts
├── hardhat-bsc-fork
│ ├── hardhat.config.js
│ ├── hardhat_bsc_fork.py
│ ├── package-lock.json
│ └── package.json
├── requirements.txt
├── simulate.py
└── simulation_api.py
```

## Getting Started

1. Make sure you have Python 3.7+ and Node.js installed on your machine.
2. Clone this repository.
3. Set up a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the required Python packages:
```
pip install -r requirements.txt
```

Install the required Node.js packages:
```
cd hardhat-bsc-fork
npm install
```
Run the Hardhat BSC fork:
```
cd hardhat-bsc-fork
node hardhat_bsc_fork.py
```

In another terminal, run the simulation API:
```
source venv/bin/activate
python simulation_api.py
```

The API should now be running on http://127.0.0.1:5000.

Usage
Use the simulation API to interact with and simulate contract executions on the BSC fork. The API provides endpoints for performing actions such as sending transactions, querying contract data, and simulating contract function calls.

Refer to the simulate.py and simulation_api.py files for implementation details and examples of how to use the API.

License
This project is licensed under the MIT License.