// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title WrappedOrbit
 * @notice ERC20 token used for bridging Orbit token to Polygon.
 */
contract WrappedOrbit is ERC20, Ownable {
    mapping(address => bool) public bridgeOperators;

    event Mint(address indexed to, uint256 amount, string orbitTxId);
    event Burn(address indexed from, uint256 amount, string orbitRecipient);

    modifier onlyBridge() {
        require(bridgeOperators[msg.sender], "Not authorized");
        _;
    }

    constructor() ERC20("Wrapped Orbit", "wORBIT") {
        // Optionally add deployer as initial bridge operator
        bridgeOperators[msg.sender] = true;
    }

    /**
     * @notice Allows the owner to add or remove bridge operator accounts.
     */
    function setBridgeOperator(address operator, bool status) external onlyOwner {
        bridgeOperators[operator] = status;
    }

    /**
     * @notice Mint tokens to user. Only callable by the bridge backend.
     * @param to Receiver address on Polygon.
     * @param amount Amount of tokens to mint.
     * @param orbitTxId The original Orbit transaction ID.
     */
    function mint(address to, uint256 amount, string memory orbitTxId) external onlyBridge {
        _mint(to, amount);
        emit Mint(to, amount, orbitTxId);
    }

    /**
     * @notice Burn tokens on Polygon to initiate a transfer back to Orbit.
     * @param amount Amount to burn.
     * @param orbitRecipient Recipient's Orbit address.
     */
    function burn(uint256 amount, string memory orbitRecipient) external {
        _burn(msg.sender, amount);
        emit Burn(msg.sender, amount, orbitRecipient);
    }
}
