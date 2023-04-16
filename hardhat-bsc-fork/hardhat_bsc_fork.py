import os
import time
import subprocess
import psutil

# Set your BSC mainnet node URL
bsc_mainnet_url = 'https://bsc-dataseed.binance.org/'

# Set the time interval for fork synchronization (5 minutes)
sync_interval_seconds = 5 * 60

# Start Hardhat node with BSC mainnet fork
def start_hardhat():
    hardhat_cmd = 'npx hardhat node'
    return subprocess.Popen(hardhat_cmd.split(), shell=True)

# Terminate the Hardhat node process
def terminate_hardhat(process):
    process.terminate()
    for child in process.children(recursive=True):
        child.terminate()

# Main function
def main():
    hardhat_process = None

    while True:
        # Terminate the previous Hardhat process if it exists
        if hardhat_process:
            terminate_hardhat(hardhat_process)
            time.sleep(2)

        # Start a new Hardhat process with the latest BSC mainnet fork
        hardhat_process = start_hardhat()
        print("Hardhat node started with BSC mainnet fork")

        # Sleep for the specified interval
        time.sleep(sync_interval_seconds)

if __name__ == "__main__":
    main()
