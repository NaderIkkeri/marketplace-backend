// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract DatasetNFT is ERC721, Ownable {
    uint256 private _nextTokenId;

    // 1. Define a structure to hold dataset information
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

    // 2. Create an array to store all datasets
    Dataset[] public allDatasets;

    // Mapping from token ID to Dataset info
    mapping(uint256 => Dataset) private _datasetInfo;

    // --- NEW: Event to log a successful purchase ---
    event DatasetPurchased(uint256 indexed tokenId, address indexed buyer, uint256 price);

    constructor() ERC721("DatasetNFT", "DSET") Ownable(msg.sender) {
        _nextTokenId = 1; // Start IDs at 1
    }

    // 3. Function for creating datasets
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

        // Store the dataset's metadata
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

    // --- NEW: Function to allow purchasing a dataset ---
    function purchaseDataset(uint256 tokenId) public payable {
        // Retrieve dataset details directly from storage
        Dataset memory dataset = _datasetInfo[tokenId];
        address seller = ownerOf(tokenId);

        // --- Require Checks ---
        // Ensure the token has a price (basic check that it exists and is for sale)
        require(dataset.price > 0, "DatasetNFT: Token does not exist or is not for sale");
        // Ensure the buyer sent enough ETH
        require(msg.value >= dataset.price, "DatasetNFT: Insufficient ETH sent");
        // Ensure the buyer is not already the owner
        require(msg.sender != seller, "DatasetNFT: Cannot purchase your own dataset");

        // --- Actions ---
        
        // 1. Transfer ETH to the seller safely
        (bool success, ) = payable(seller).call{value: dataset.price}("");
        require(success, "DatasetNFT: Transfer to seller failed");

        // 2. Emit event to log the purchase on-chain
        emit DatasetPurchased(tokenId, msg.sender, dataset.price);

        // 3. (Optional) Refund excess ETH if they sent too much
        if (msg.value > dataset.price) {
            payable(msg.sender).transfer(msg.value - dataset.price);
        }
    }

    // 4. Function to get all datasets
    function getAllDatasets() public view returns (Dataset[] memory) {
        return allDatasets;
    }

    // 5. Function to get details of a single dataset
    function getDatasetById(uint256 tokenId) public view returns (Dataset memory) {
        return _datasetInfo[tokenId];
    }
    // NEW: Helper function to get all datasets owned by a specific user
    function getDatasetsByOwner(address _owner) public view returns (Dataset[] memory) {
        uint256 totalItemCount = allDatasets.length;
        uint256 ownedItemCount = balanceOf(_owner);
        
        // Create a fixed-size array for the results
        Dataset[] memory ownedDatasets = new Dataset[](ownedItemCount);
        uint256 currentIndex = 0;

        for (uint256 i = 0; i < totalItemCount; i++) {
            // Important: Use ownerOf() to check current ownership, 
            // not just the original creator stored in the struct.
            // Assuming IDs start at 1 based on your constructor.
            uint256 tokenId = allDatasets[i].id;
            if (ownerOf(tokenId) == _owner) {
                ownedDatasets[currentIndex] = allDatasets[i];
                currentIndex += 1;
            }
        }
        return ownedDatasets;
    }
}
