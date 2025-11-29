// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract DatasetNFT is ERC721, Ownable {
    uint256 private _nextTokenId;

    struct Dataset {
        uint256 id;
        string name;
        string description;
        string category;
        string format;
        string ipfsCid;
        uint256 price;
        address owner;
    }

    Dataset[] public allDatasets;
    mapping(uint256 => Dataset) private _datasetInfo;

    // --- RENTAL MAPPINGS ---
    // TokenID -> Daily Price in Wei
    mapping(uint256 => uint256) public rentalPrices;
    // TokenID -> Renter Address -> Expiry Timestamp
    mapping(uint256 => mapping(address => uint256)) public rentalExpirations;

    // --- DASHBOARD MAPPINGS ---
    // Mapping to keep track of which token IDs a wallet has purchased (Lifetime Access)
    mapping(address => uint256[]) private _purchasedDatasets;

    // --- EVENTS ---
    event DatasetPurchased(uint256 indexed tokenId, address indexed buyer, address indexed seller, uint256 price);
    event DatasetRented(uint256 indexed tokenId, address indexed renter, address indexed owner, uint256 expiresAt, uint256 amountPaid);
    event PaymentReceived(address indexed from, uint256 amount);
    event EmergencyWithdrawal(address indexed to, uint256 amount);

    constructor() ERC721("DatasetNFT", "DSET") Ownable(msg.sender) {
        _nextTokenId = 1; 
    }

    // 1. Create Dataset
    function createDataset(
        string memory name,
        string memory description,
        string memory category,
        string memory format,
        string memory ipfsCid,
        uint256 price
    ) public {
        uint256 tokenId = _nextTokenId;
        _nextTokenId++;

        _safeMint(msg.sender, tokenId);

        Dataset memory newDataset = Dataset({
            id: tokenId,
            name: name,
            description: description,
            category: category,
            format: format,
            ipfsCid: ipfsCid,
            price: price,
            owner: msg.sender
        });

        _datasetInfo[tokenId] = newDataset;
        allDatasets.push(newDataset);
    }

    // 2. Purchase Dataset (Lifetime Access)
    function purchaseDataset(uint256 tokenId) public payable {
        Dataset memory dataset = _datasetInfo[tokenId];
        address seller = ownerOf(tokenId);

        require(dataset.price > 0, "Not for sale");
        require(msg.value >= dataset.price, "Insufficient ETH sent");
        require(msg.sender != seller, "Cannot buy your own dataset");

        // Transfer ETH to seller
        (bool success, ) = payable(seller).call{value: dataset.price}("");
        require(success, "Transfer failed");

        // Refund excess
        if (msg.value > dataset.price) {
            payable(msg.sender).transfer(msg.value - dataset.price);
        }

        // Add to buyer's list (Fixes the Dashboard loading issue)
        _purchasedDatasets[msg.sender].push(tokenId);

        emit DatasetPurchased(tokenId, msg.sender, seller, dataset.price);
    }

    // 3. Set Rental Price (Only Owner)
    function setRentalPrice(uint256 tokenId, uint256 pricePerDay) public {
        require(ownerOf(tokenId) == msg.sender, "Only owner can set price");
        rentalPrices[tokenId] = pricePerDay;
    }

    // 4. Rent Dataset (Temporary Access)
    function rentDataset(uint256 tokenId, uint256 daysToRent) public payable {
        uint256 pricePerDay = rentalPrices[tokenId];
        require(pricePerDay > 0, "This dataset is not for rent");
        
        uint256 totalCost = pricePerDay * daysToRent;
        require(msg.value >= totalCost, "Insufficient ETH sent for rental");

        address owner = ownerOf(tokenId);
        
        // Transfer funds
        (bool sent, ) = payable(owner).call{value: totalCost}("");
        require(sent, "Transfer failed");

        // Calculate expiration
        uint256 currentExpiry = rentalExpirations[tokenId][msg.sender];
        uint256 newExpiry;

        if (currentExpiry > block.timestamp) {
            // Extend existing rental
            newExpiry = currentExpiry + (daysToRent * 1 days);
        } else {
            // New rental
            newExpiry = block.timestamp + (daysToRent * 1 days);
        }

        rentalExpirations[tokenId][msg.sender] = newExpiry;

        // Refund excess
        if (msg.value > totalCost) {
            payable(msg.sender).transfer(msg.value - totalCost);
        }

        emit DatasetRented(tokenId, msg.sender, owner, newExpiry, totalCost);
    }

    // --- EMERGENCY FUNCTIONS ---

    /**
     * @notice Withdraw any ETH accidentally sent to the contract
     * @dev Only contract owner can call this. Should only contain dust/accidental transfers.
     */
    function emergencyWithdraw() external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to withdraw");

        (bool success, ) = payable(owner()).call{value: balance}("");
        require(success, "Withdrawal failed");

        emit EmergencyWithdrawal(owner(), balance);
    }

    /**
     * @notice Fallback to receive ETH sent directly to contract
     * @dev Emits event for tracking
     */
    receive() external payable {
        emit PaymentReceived(msg.sender, msg.value);
    }

    /**
     * @notice Get the contract's ETH balance
     * @dev This should normally be 0 or very small (dust from overpayments)
     */
    function getContractBalance() external view returns (uint256) {
        return address(this).balance;
    }

    // --- READ FUNCTIONS ---

    function getAllDatasets() public view returns (Dataset[] memory) {
        return allDatasets;
    }

    function getDatasetById(uint256 tokenId) public view returns (Dataset memory) {
        return _datasetInfo[tokenId];
    }

    // Get all datasets owned by a specific user (Minted)
    function getDatasetsByOwner(address _owner) public view returns (Dataset[] memory) {
        uint256 totalItemCount = allDatasets.length;
        uint256 ownedItemCount = balanceOf(_owner);
        
        Dataset[] memory ownedDatasets = new Dataset[](ownedItemCount);
        uint256 currentIndex = 0;

        for (uint256 i = 0; i < totalItemCount; i++) {
            uint256 tokenId = allDatasets[i].id;
            if (ownerOf(tokenId) == _owner) {
                ownedDatasets[currentIndex] = allDatasets[i];
                currentIndex += 1;
            }
        }
        return ownedDatasets;
    }

    // Get all datasets purchased by the user (Lifetime Access)
    function getMyPurchasedDatasets() public view returns (uint256[] memory) {
        return _purchasedDatasets[msg.sender];
    }

    // Check if a user has active access (Owner OR Purchased OR Rented)
    function hasAccess(uint256 tokenId, address user) public view returns (bool) {
        // 1. Is Owner?
        if (ownerOf(tokenId) == user) return true;

        // 2. Has Rented?
        if (rentalExpirations[tokenId][user] > block.timestamp) return true;

        // 3. Has Purchased?
        uint256[] memory purchasedIds = _purchasedDatasets[user];
        for(uint256 i = 0; i < purchasedIds.length; i++) {
            if (purchasedIds[i] == tokenId) return true;
        }

        return false;
    }
}