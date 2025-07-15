"""Unit tests for eBay prompts.

Tests the prompt implementations with mocked context and validates output.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from fastmcp import Context

from prompts.search_assistant import item_search_assistant_prompt
from prompts.listing_optimizer import listing_optimizer_prompt
from prompts.deal_finder import deal_finder_prompt
from prompts.market_researcher import market_researcher_prompt


class TestSearchAssistantPrompt:
    """Test search assistant prompt."""
    
    @pytest.mark.asyncio
    async def test_search_assistant_default_parameters(self):
        """Test search assistant with default parameters."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await item_search_assistant_prompt.fn(ctx=ctx)
        
        # Verify context was called
        ctx.info.assert_called_once_with("Search assistant prompt activated")
        
        # Verify result content
        assert isinstance(result, str)
        assert len(result) > 1000  # Should be substantial content
        assert "eBay Search Assistant" in result
        assert "search_items" in result
        assert "find_items_by_category" in result
        assert "get_search_keywords" in result
        assert "find_items_advanced" in result
    
    @pytest.mark.asyncio
    async def test_search_assistant_custom_name(self):
        """Test search assistant with custom name."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await item_search_assistant_prompt.fn(name="John", ctx=ctx)
        
        assert "eBay Search Assistant for John" in result
        ctx.info.assert_called_once_with("Search assistant prompt activated")
    
    @pytest.mark.asyncio
    async def test_search_assistant_content_structure(self):
        """Test that search assistant has expected content sections."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await item_search_assistant_prompt.fn(ctx=ctx)
        
        # Check for key sections
        assert "🎯 What are you trying to accomplish?" in result
        assert "🧠 Smart Search Decision Tree" in result
        assert "🛠️ Tool Selection Guide" in result
        assert "💡 Advanced Search Strategies" in result
        assert "🎯 Common Search Scenarios & Solutions" in result
        assert "🏆 Pro Tips for eBay Success" in result
        assert "🚀 Ready to Search?" in result
    
    @pytest.mark.asyncio
    async def test_search_assistant_tool_references(self):
        """Test that all Finding API tools are referenced."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await item_search_assistant_prompt.fn(ctx=ctx)
        
        # Check for all Finding API tools
        assert "`search_items`" in result
        assert "`find_items_by_category`" in result
        assert "`find_items_advanced`" in result
        assert "`get_search_keywords`" in result


class TestListingOptimizerPrompt:
    """Test listing optimizer prompt."""
    
    @pytest.mark.asyncio
    async def test_listing_optimizer_default_parameters(self):
        """Test listing optimizer with default parameters."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await listing_optimizer_prompt.fn(ctx=ctx)
        
        # Verify context was called
        ctx.info.assert_called_once_with("Listing optimizer prompt activated for product")
        
        # Verify result content
        assert isinstance(result, str)
        assert len(result) > 2000  # Should be substantial content
        assert "eBay Listing Optimizer" in result
        assert "Product Edition" in result
    
    @pytest.mark.asyncio
    async def test_listing_optimizer_custom_item_type(self):
        """Test listing optimizer with custom item type."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await listing_optimizer_prompt.fn(item_type="electronics", ctx=ctx)
        
        assert "Electronics Edition" in result
        assert "Electronics (electronics)" in result
        ctx.info.assert_called_once_with("Listing optimizer prompt activated for electronics")
    
    @pytest.mark.asyncio
    async def test_listing_optimizer_content_structure(self):
        """Test that listing optimizer has expected content sections."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await listing_optimizer_prompt.fn(ctx=ctx)
        
        # Check for key sections
        assert "🎯 Listing Optimization Checklist" in result
        assert "📝 Title Optimization Strategies" in result
        assert "💰 Strategic Pricing Guide" in result
        assert "📸 Photo Optimization Secrets" in result
        assert "✍️ Description Optimization" in result
        assert "🎨 Category-Specific Optimization" in result
        assert "🚚 Shipping & Handling Strategy" in result
        assert "📊 Performance Optimization" in result
        assert "🏆 Advanced Listing Tactics" in result
    
    @pytest.mark.asyncio
    async def test_listing_optimizer_optimization_elements(self):
        """Test that key optimization elements are covered."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await listing_optimizer_prompt.fn(ctx=ctx)
        
        # Check for optimization topics
        assert "Title Optimization" in result
        assert "Category Selection" in result
        assert "Pricing Strategy" in result
        assert "Photos & Presentation" in result
        assert "Description & Details" in result
        assert "Power Words" in result
        assert "SEO Optimization" in result


class TestDealFinderPrompt:
    """Test deal finder prompt."""
    
    @pytest.mark.asyncio
    async def test_deal_finder_default_parameters(self):
        """Test deal finder with default parameters."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await deal_finder_prompt.fn(ctx=ctx)
        
        # Verify context was called
        ctx.info.assert_called_once_with("Deal finder prompt activated - Budget: flexible, Category: any")
        
        # Verify result content
        assert isinstance(result, str)
        assert len(result) > 2000  # Should be substantial content
        assert "eBay Deal Hunter" in result
        assert "Flexible Budget | Any Focus" in result
    
    @pytest.mark.asyncio
    async def test_deal_finder_custom_parameters(self):
        """Test deal finder with custom parameters."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await deal_finder_prompt.fn(budget="tight", category="electronics", ctx=ctx)
        
        assert "Tight Budget | Electronics Focus" in result
        ctx.info.assert_called_once_with("Deal finder prompt activated - Budget: tight, Category: electronics")
    
    @pytest.mark.asyncio
    async def test_deal_finder_content_structure(self):
        """Test that deal finder has expected content sections."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await deal_finder_prompt.fn(ctx=ctx)
        
        # Check for key sections
        assert "💰 Deal Hunting Philosophy" in result
        assert "🎯 Deal Hunter's Toolkit" in result
        assert "⏰ Strategic Timing Guide" in result
        assert "🔍 Advanced Deal Hunting Strategies" in result
        assert "💡 Category-Specific Deal Tactics" in result
        assert "🚨 Deal Verification Checklist" in result
        assert "🎲 Risk Assessment Matrix" in result
        assert "🏆 Advanced Deal Hunter Tactics" in result
    
    @pytest.mark.asyncio
    async def test_deal_finder_strategies(self):
        """Test that key deal hunting strategies are included."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await deal_finder_prompt.fn(ctx=ctx)
        
        # Check for deal hunting strategies
        assert "Misspelling Strategy" in result
        assert "Auction Sniping Strategy" in result
        assert "Bundle Breaking Strategy" in result
        assert "Incomplete Search Strategy" in result
        assert "Sunday Night Special" in result
        assert "Risk Assessment Matrix" in result


class TestMarketResearcherPrompt:
    """Test market researcher prompt."""
    
    @pytest.mark.asyncio
    async def test_market_researcher_default_parameters(self):
        """Test market researcher with default parameters."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await market_researcher_prompt.fn(ctx=ctx)
        
        # Verify context was called
        ctx.info.assert_called_once_with("Market researcher prompt activated - Research: general, Focus: any")
        
        # Verify result content
        assert isinstance(result, str)
        assert len(result) > 3000  # Should be substantial content
        assert "eBay Market Research Center" in result
        assert "General Analysis | Any Focus" in result
    
    @pytest.mark.asyncio
    async def test_market_researcher_custom_parameters(self):
        """Test market researcher with custom parameters."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await market_researcher_prompt.fn(
            research_type="pricing", 
            market_focus="collectibles", 
            ctx=ctx
        )
        
        assert "Pricing Analysis | Collectibles Focus" in result
        ctx.info.assert_called_once_with("Market researcher prompt activated - Research: pricing, Focus: collectibles")
    
    @pytest.mark.asyncio
    async def test_market_researcher_content_structure(self):
        """Test that market researcher has expected content sections."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await market_researcher_prompt.fn(ctx=ctx)
        
        # Check for key sections
        assert "📊 Market Research Objectives" in result
        assert "🛠️ Research Methodology Framework" in result
        assert "📈 Market Analysis Techniques" in result
        assert "🔍 Advanced Research Techniques" in result
        assert "📊 Market Research Templates" in result
        assert "🎯 Research Action Plans" in result
        assert "🚨 Research Quality Checklist" in result
    
    @pytest.mark.asyncio
    async def test_market_researcher_analysis_methods(self):
        """Test that key analysis methods are included."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        result = await market_researcher_prompt.fn(ctx=ctx)
        
        # Check for analysis frameworks
        assert "STAR Analysis Method" in result
        assert "Price Point Analysis" in result
        assert "Demand Analysis Framework" in result
        assert "Competitive Landscape Mapping" in result
        assert "Seasonal Trend Analysis" in result
        assert "Market Opportunity Assessment" in result
        assert "GAP Analysis" in result


class TestPromptParameterHandling:
    """Test parameter handling across all prompts."""
    
    @pytest.mark.asyncio
    async def test_search_assistant_parameter_types(self):
        """Test search assistant handles different parameter types."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        # Test with empty string
        result = await item_search_assistant_prompt.fn(name="", ctx=ctx)
        assert "eBay Search Assistant for " in result
        
        # Test with special characters
        result = await item_search_assistant_prompt.fn(name="Tech & Electronics", ctx=ctx)
        assert "Tech & Electronics" in result
    
    @pytest.mark.asyncio
    async def test_listing_optimizer_parameter_types(self):
        """Test listing optimizer handles different item types."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        test_types = ["electronics", "clothing", "collectibles", "automotive"]
        
        for item_type in test_types:
            result = await listing_optimizer_prompt.fn(item_type=item_type, ctx=ctx)
            assert item_type.title() in result
            assert f"Electronics ({item_type})" in result
    
    @pytest.mark.asyncio
    async def test_deal_finder_parameter_combinations(self):
        """Test deal finder with various parameter combinations."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        combinations = [
            ("tight", "electronics"),
            ("moderate", "fashion"),
            ("flexible", "collectibles")
        ]
        
        for budget, category in combinations:
            result = await deal_finder_prompt.fn(budget=budget, category=category, ctx=ctx)
            assert budget.title() in result
            assert category.title() in result
    
    @pytest.mark.asyncio
    async def test_market_researcher_parameter_combinations(self):
        """Test market researcher with various parameter combinations."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        combinations = [
            ("pricing", "electronics"),
            ("demand", "fashion"),
            ("competition", "collectibles"),
            ("trends", "automotive")
        ]
        
        for research_type, market_focus in combinations:
            result = await market_researcher_prompt.fn(
                research_type=research_type, 
                market_focus=market_focus, 
                ctx=ctx
            )
            assert research_type.title() in result
            assert market_focus.title() in result


class TestPromptContentQuality:
    """Test the quality and completeness of prompt content."""
    
    @pytest.mark.asyncio
    async def test_all_prompts_have_substantial_content(self):
        """Test that all prompts generate substantial content."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        prompts = [
            item_search_assistant_prompt,
            listing_optimizer_prompt,
            deal_finder_prompt,
            market_researcher_prompt
        ]
        
        for prompt_func in prompts:
            result = await prompt_func.fn(ctx=ctx)
            assert len(result) > 1000, f"{prompt_func.fn.__name__} should generate substantial content"
            assert result.strip() != "", f"{prompt_func.fn.__name__} should not return empty content"
    
    @pytest.mark.asyncio
    async def test_all_prompts_include_emojis_and_formatting(self):
        """Test that prompts use proper formatting and emojis."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        prompts = [
            item_search_assistant_prompt,
            listing_optimizer_prompt,
            deal_finder_prompt,
            market_researcher_prompt
        ]
        
        for prompt_func in prompts:
            result = await prompt_func.fn(ctx=ctx)
            # Should include emojis for visual appeal
            assert any(char in result for char in "🎯📊💡🚀⚡🔍💰📈🏆"), f"{prompt_func.fn.__name__} should include emojis"
            # Should include markdown formatting
            assert "##" in result, f"{prompt_func.fn.__name__} should include section headers"
            assert "###" in result, f"{prompt_func.fn.__name__} should include subsection headers"
    
    @pytest.mark.asyncio
    async def test_all_prompts_reference_relevant_tools(self):
        """Test that prompts reference relevant eBay tools."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        # Search assistant should reference Finding API tools
        result = await item_search_assistant_prompt.fn(ctx=ctx)
        finding_tools = ["`search_items`", "`find_items_by_category`", "`find_items_advanced`", "`get_search_keywords`"]
        for tool in finding_tools:
            assert tool in result, f"Search assistant should reference {tool}"
        
        # Deal finder should reference relevant tools
        result = await deal_finder_prompt.fn(ctx=ctx)
        deal_tools = ["`find_items_advanced`", "`search_items`", "`get_deals`"]
        for tool in deal_tools:
            assert tool in result, f"Deal finder should reference {tool}"
        
        # Market researcher should reference research tools
        result = await market_researcher_prompt.fn(ctx=ctx)
        research_tools = ["`search_items`", "`find_items_advanced`", "`get_search_keywords`", "`get_most_watched_items`"]
        for tool in research_tools:
            assert tool in result, f"Market researcher should reference {tool}"


class TestPromptErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_prompts_handle_context_errors(self):
        """Test prompts handle context call failures gracefully."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock(side_effect=Exception("Context error"))
        
        # Should still return content even if context fails
        result = await item_search_assistant_prompt.fn(ctx=ctx)
        assert isinstance(result, str)
        assert len(result) > 100
        
        # Context should have been called despite error
        ctx.info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_prompts_handle_none_parameters(self):
        """Test prompts handle None parameters gracefully."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        # Test with None values (should use defaults)
        result = await listing_optimizer_prompt.fn(item_type=None, ctx=ctx)
        assert isinstance(result, str)
        assert "Product Edition" in result  # Should handle None gracefully by using default
    
    @pytest.mark.asyncio
    async def test_prompts_handle_empty_parameters(self):
        """Test prompts handle empty string parameters."""
        ctx = Mock(spec=Context)
        ctx.info = AsyncMock()
        
        # Test with empty strings (should use defaults)
        result = await deal_finder_prompt.fn(budget="", category="", ctx=ctx)
        assert isinstance(result, str)
        assert "Flexible Budget | Any Focus" in result  # Should handle empty strings by using defaults