// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract DatasetNFT is ERC721, Ownable {
    constructor() ERC721("DatasetNFT", "DSET") Ownable(msg.sender) {}

    function safeMint(address to, string memory uri) public onlyOwner {
        uint256 tokenId = uint256(keccak256(abi.encodePacked(uri)));
        _safeMint(to, tokenId);
    }
}