require("@nomiclabs/hardhat-ethers");

const ALCHEMY_API_KEY = "<YOUR_ALCHEMY_API_KEY>";

module.exports = {
  defaultNetwork: "hardhat",
  networks: {
    hardhat: {
      chainId: 56, // BSC Mainnet Chain ID
      forking: {
        url: `https://bsc-dataseed.binance.org/`,
        // Or use your Alchemy API Key
        // url: `https://eth-mainnet.alchemyapi.io/v2/${ALCHEMY_API_KEY}`,
      },
      allowUnlimitedContractSize: true
    },
  },
  solidity: {
    version: "0.8.4",
  },
};
