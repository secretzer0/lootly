"""Unit tests for Taxonomy API tools."""
import pytest

from tools.taxonomy_api import (
    _convert_category_node,
    _convert_category_subtree
)


class TestDataConversion:
    """Test data conversion functions."""
    
    def test_convert_category_node_complete(self):
        """Test conversion with complete category node."""
        node = {
            "categoryId": "267",
            "categoryName": "Books, Movies & Music",
            "categoryTreeNodeLevel": 1,
            "leafCategory": False,
            "parentCategoryNodeHref": "https://api.ebay.com/commerce/taxonomy/v1/category_tree/0/get_category_subtree?category_id=20081",
            "categorySubtreeNodeHref": "https://api.ebay.com/commerce/taxonomy/v1/category_tree/0/get_category_subtree?category_id=267",
            "childCategoryTreeNodes": [
                {
                    "categoryId": "458",
                    "categoryName": "Books & Magazines",
                    "categoryTreeNodeLevel": 2,
                    "leafCategory": True
                }
            ]
        }
        
        result = _convert_category_node(node)
        
        assert result["category_id"] == "267"
        assert result["category_name"] == "Books, Movies & Music"
        assert result["level"] == 1
        assert result["leaf"] == False
        assert result["child_count"] == 1
        assert result["has_children"] == True
    
    def test_convert_category_node_minimal(self):
        """Test conversion with minimal category node."""
        node = {
            "categoryId": "123",
            "categoryName": "Test Category"
        }
        
        result = _convert_category_node(node)
        
        assert result["category_id"] == "123"
        assert result["category_name"] == "Test Category"
        assert result["level"] == 1  # Default value
        assert result["leaf"] == False  # Default value
        assert result["child_count"] == 0
        assert result["has_children"] == False
    
    def test_convert_category_subtree_root(self):
        """Test conversion of category subtree with root node."""
        subtree = {
            "categoryId": "267",
            "categoryName": "Books, Movies & Music",
            "categoryTreeNodeLevel": 1,
            "leafCategory": False,
            "childCategoryTreeNodes": [
                {
                    "categoryId": "458",
                    "categoryName": "Books & Magazines",
                    "categoryTreeNodeLevel": 2,
                    "leafCategory": True
                }
            ]
        }
        
        result = _convert_category_subtree(subtree)
        
        assert len(result) == 2  # Root + child
        assert result[0]["category_id"] == "267"
        assert result[0]["category_name"] == "Books, Movies & Music"
        assert result[0]["level"] == 1
        assert result[0]["child_count"] == 1
        assert result[0]["has_children"] == True
        assert result[1]["category_id"] == "458"
        assert result[1]["category_name"] == "Books & Magazines"
        assert result[1]["leaf"] == True