# Import required Flask modules
from flask import Flask, request, jsonify
from simulate import MockContract

# Create a Flask app
app = Flask(__name__)

# Define the POST request endpoint
@app.route('/api/mock_call', methods=['POST'])
def mock_call():
    data = request.get_json()

    if 'contract_address' not in data or 'sender_address' not in data or 'value' not in data or 'function_name' not in data:
        return jsonify({"error": "Missing required parameters"}), 400

    contract_address = data['contract_address']
    sender_address = data['sender_address']
    value = data['value']
    function_name = data['function_name']

    # Initialize the Mock_Contract object with the given contract address
    mock_contract = MockContract(contract_address)

    # Call the mock_call_contract_function and pass the necessary parameters
    result = mock_contract.mock_call_contract_function(sender_address, value, function_name, *data.get('args', []), **data.get('kwargs', {}))

    return jsonify(result)

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
