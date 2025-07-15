"""Import tests for eBay prompts.

Tests that all prompt modules can be imported successfully and have expected exports.
"""
import pytest


class TestPromptImports:
    """Test prompt module imports."""
    
    def test_search_assistant_import(self):
        """Test search assistant prompt can be imported."""
        from prompts.search_assistant import item_search_assistant_prompt
        from fastmcp.prompts.prompt import FunctionPrompt
        
        # Verify it's a FunctionPrompt (decorated with @mcp.prompt)
        assert isinstance(item_search_assistant_prompt, FunctionPrompt)
        
        # Verify the underlying function is callable
        assert callable(item_search_assistant_prompt.fn)
        
        # Verify function name
        assert item_search_assistant_prompt.fn.__name__ == "item_search_assistant_prompt"
    
    def test_listing_optimizer_import(self):
        """Test listing optimizer prompt can be imported."""
        from prompts.listing_optimizer import listing_optimizer_prompt
        from fastmcp.prompts.prompt import FunctionPrompt
        
        # Verify it's a FunctionPrompt (decorated with @mcp.prompt)
        assert isinstance(listing_optimizer_prompt, FunctionPrompt)
        
        # Verify the underlying function is callable
        assert callable(listing_optimizer_prompt.fn)
        
        # Verify function name
        assert listing_optimizer_prompt.fn.__name__ == "listing_optimizer_prompt"
    
    def test_deal_finder_import(self):
        """Test deal finder prompt can be imported."""
        from prompts.deal_finder import deal_finder_prompt
        from fastmcp.prompts.prompt import FunctionPrompt
        
        # Verify it's a FunctionPrompt (decorated with @mcp.prompt)
        assert isinstance(deal_finder_prompt, FunctionPrompt)
        
        # Verify the underlying function is callable
        assert callable(deal_finder_prompt.fn)
        
        # Verify function name
        assert deal_finder_prompt.fn.__name__ == "deal_finder_prompt"
    
    def test_market_researcher_import(self):
        """Test market researcher prompt can be imported."""
        from prompts.market_researcher import market_researcher_prompt
        from fastmcp.prompts.prompt import FunctionPrompt
        
        # Verify it's a FunctionPrompt (decorated with @mcp.prompt)
        assert isinstance(market_researcher_prompt, FunctionPrompt)
        
        # Verify the underlying function is callable
        assert callable(market_researcher_prompt.fn)
        
        # Verify function name
        assert market_researcher_prompt.fn.__name__ == "market_researcher_prompt"


class TestPromptModuleStructure:
    """Test prompt module structure and dependencies."""
    
    def test_all_prompts_have_context_parameter(self):
        """Test that all prompt functions accept Context parameter."""
        from prompts.search_assistant import item_search_assistant_prompt
        from prompts.listing_optimizer import listing_optimizer_prompt
        from prompts.deal_finder import deal_finder_prompt
        from prompts.market_researcher import market_researcher_prompt
        
        import inspect
        
        prompts = [
            item_search_assistant_prompt,
            listing_optimizer_prompt,
            deal_finder_prompt,
            market_researcher_prompt
        ]
        
        for prompt_func in prompts:
            sig = inspect.signature(prompt_func.fn)
            assert "ctx" in sig.parameters, f"{prompt_func.fn.__name__} missing ctx parameter"
            assert sig.parameters["ctx"].kind == inspect.Parameter.KEYWORD_ONLY, f"{prompt_func.fn.__name__} ctx must be keyword-only"
    
    def test_all_prompts_are_async(self):
        """Test that all prompt functions are async."""
        from prompts.search_assistant import item_search_assistant_prompt
        from prompts.listing_optimizer import listing_optimizer_prompt
        from prompts.deal_finder import deal_finder_prompt
        from prompts.market_researcher import market_researcher_prompt
        
        import inspect
        
        prompts = [
            item_search_assistant_prompt,
            listing_optimizer_prompt,
            deal_finder_prompt,
            market_researcher_prompt
        ]
        
        for prompt_func in prompts:
            assert inspect.iscoroutinefunction(prompt_func.fn), f"{prompt_func.fn.__name__} should be async"
    
    def test_prompts_have_optional_parameters(self):
        """Test that prompts have appropriate optional parameters."""
        from prompts.search_assistant import item_search_assistant_prompt
        from prompts.listing_optimizer import listing_optimizer_prompt
        from prompts.deal_finder import deal_finder_prompt
        from prompts.market_researcher import market_researcher_prompt
        
        import inspect
        
        # Test search assistant has name parameter
        search_sig = inspect.signature(item_search_assistant_prompt.fn)
        assert "name" in search_sig.parameters
        assert search_sig.parameters["name"].default is not inspect.Parameter.empty
        
        # Test listing optimizer has item_type parameter
        listing_sig = inspect.signature(listing_optimizer_prompt.fn)
        assert "item_type" in listing_sig.parameters
        assert listing_sig.parameters["item_type"].default is not inspect.Parameter.empty
        
        # Test deal finder has budget and category parameters
        deal_sig = inspect.signature(deal_finder_prompt.fn)
        assert "budget" in deal_sig.parameters
        assert "category" in deal_sig.parameters
        assert deal_sig.parameters["budget"].default is not inspect.Parameter.empty
        assert deal_sig.parameters["category"].default is not inspect.Parameter.empty
        
        # Test market researcher has research_type and market_focus parameters
        research_sig = inspect.signature(market_researcher_prompt.fn)
        assert "research_type" in research_sig.parameters
        assert "market_focus" in research_sig.parameters
        assert research_sig.parameters["research_type"].default is not inspect.Parameter.empty
        assert research_sig.parameters["market_focus"].default is not inspect.Parameter.empty
    
    def test_required_dependencies_available(self):
        """Test that required dependencies can be imported."""
        # Test MCP dependency
        from fastmcp import Context
        assert Context is not None


class TestPromptExports:
    """Test that prompt modules export expected symbols."""
    
    def test_search_assistant_exports(self):
        """Test search assistant module exports."""
        import prompts.search_assistant as search_module
        
        # Required exports
        required_exports = [
            "item_search_assistant_prompt"
        ]
        
        for export in required_exports:
            assert hasattr(search_module, export), f"Missing export: {export}"
    
    def test_listing_optimizer_exports(self):
        """Test listing optimizer module exports."""
        import prompts.listing_optimizer as listing_module
        
        # Required exports
        required_exports = [
            "listing_optimizer_prompt"
        ]
        
        for export in required_exports:
            assert hasattr(listing_module, export), f"Missing export: {export}"
    
    def test_deal_finder_exports(self):
        """Test deal finder module exports."""
        import prompts.deal_finder as deal_module
        
        # Required exports
        required_exports = [
            "deal_finder_prompt"
        ]
        
        for export in required_exports:
            assert hasattr(deal_module, export), f"Missing export: {export}"
    
    def test_market_researcher_exports(self):
        """Test market researcher module exports."""
        import prompts.market_researcher as research_module
        
        # Required exports
        required_exports = [
            "market_researcher_prompt"
        ]
        
        for export in required_exports:
            assert hasattr(research_module, export), f"Missing export: {export}"
    
    def test_no_unexpected_public_exports(self):
        """Test that modules don't have unexpected public exports."""
        import prompts.search_assistant as search_module
        import prompts.listing_optimizer as listing_module
        import prompts.deal_finder as deal_module
        import prompts.market_researcher as research_module
        
        modules = [
            (search_module, "search_assistant"),
            (listing_module, "listing_optimizer"),
            (deal_module, "deal_finder"),
            (research_module, "market_researcher")
        ]
        
        for module, name in modules:
            # Get all public exports (not starting with _)
            public_exports = [attr for attr in dir(module) if not attr.startswith('_')]
            
            # Should have minimal exports (main function + any re-exports)
            assert len(public_exports) <= 10, f"{name} has too many public exports: {public_exports}"
            
            # Should have the main prompt function
            main_function = f"{name.replace('_', '_')}_prompt" if name != "search_assistant" else "item_search_assistant_prompt"
            assert main_function in public_exports, f"{name} missing main function {main_function}"


class TestPromptDocstrings:
    """Test that prompt functions have proper docstrings."""
    
    def test_all_prompts_have_docstrings(self):
        """Test that all prompt functions have docstrings."""
        from prompts.search_assistant import item_search_assistant_prompt
        from prompts.listing_optimizer import listing_optimizer_prompt
        from prompts.deal_finder import deal_finder_prompt
        from prompts.market_researcher import market_researcher_prompt
        
        prompts = [
            item_search_assistant_prompt,
            listing_optimizer_prompt,
            deal_finder_prompt,
            market_researcher_prompt
        ]
        
        for prompt_func in prompts:
            assert prompt_func.fn.__doc__ is not None, f"{prompt_func.fn.__name__} missing docstring"
            assert len(prompt_func.fn.__doc__.strip()) > 50, f"{prompt_func.fn.__name__} docstring too short"
    
    def test_docstrings_include_args_and_returns(self):
        """Test that docstrings include Args and Returns sections."""
        from prompts.search_assistant import item_search_assistant_prompt
        from prompts.listing_optimizer import listing_optimizer_prompt
        from prompts.deal_finder import deal_finder_prompt
        from prompts.market_researcher import market_researcher_prompt
        
        prompts = [
            item_search_assistant_prompt,
            listing_optimizer_prompt,
            deal_finder_prompt,
            market_researcher_prompt
        ]
        
        for prompt_func in prompts:
            docstring = prompt_func.fn.__doc__
            assert "Args:" in docstring, f"{prompt_func.fn.__name__} docstring missing Args section"
            assert "Returns:" in docstring, f"{prompt_func.fn.__name__} docstring missing Returns section"
            assert "ctx" in docstring, f"{prompt_func.fn.__name__} docstring should mention ctx parameter"


class TestPromptInitialization:
    """Test prompt package initialization."""
    
    def test_prompts_package_import(self):
        """Test that prompts package can be imported."""
        import prompts
        assert prompts is not None
    
    def test_prompts_init_file_exists(self):
        """Test that prompts/__init__.py exists and is importable."""
        from prompts import __init__
        assert __init__ is not None
    
    def test_can_import_all_prompts_from_package(self):
        """Test that all prompts can be imported from package."""
        # This verifies the package structure is correct
        try:
            from prompts.search_assistant import item_search_assistant_prompt
            from prompts.listing_optimizer import listing_optimizer_prompt
            from prompts.deal_finder import deal_finder_prompt
            from prompts.market_researcher import market_researcher_prompt
            success = True
        except ImportError:
            success = False
        
        assert success, "Could not import all prompts from package"
    
    def test_prompt_modules_are_independent(self):
        """Test that prompt modules can be imported independently."""
        # Test each module can be imported without the others
        modules = [
            "prompts.search_assistant",
            "prompts.listing_optimizer", 
            "prompts.deal_finder",
            "prompts.market_researcher"
        ]
        
        for module_name in modules:
            try:
                __import__(module_name)
                success = True
            except ImportError:
                success = False
            
            assert success, f"Could not import {module_name} independently"


class TestPromptConsistency:
    """Test consistency across prompt modules."""
    
    def test_all_prompts_return_strings(self):
        """Test that all prompt functions have string return type hints."""
        from prompts.search_assistant import item_search_assistant_prompt
        from prompts.listing_optimizer import listing_optimizer_prompt
        from prompts.deal_finder import deal_finder_prompt
        from prompts.market_researcher import market_researcher_prompt
        
        import inspect
        
        prompts = [
            item_search_assistant_prompt,
            listing_optimizer_prompt,
            deal_finder_prompt,
            market_researcher_prompt
        ]
        
        for prompt_func in prompts:
            sig = inspect.signature(prompt_func.fn)
            # Check if return annotation exists and is str
            if sig.return_annotation != inspect.Signature.empty:
                assert sig.return_annotation == str, f"{prompt_func.fn.__name__} should return str"
    
    def test_consistent_parameter_naming(self):
        """Test that all prompts use consistent parameter naming."""
        from prompts.search_assistant import item_search_assistant_prompt
        from prompts.listing_optimizer import listing_optimizer_prompt
        from prompts.deal_finder import deal_finder_prompt
        from prompts.market_researcher import market_researcher_prompt
        
        import inspect
        
        # All should have 'ctx' as keyword-only parameter
        prompts = [
            item_search_assistant_prompt,
            listing_optimizer_prompt,
            deal_finder_prompt,
            market_researcher_prompt
        ]
        
        for prompt_func in prompts:
            sig = inspect.signature(prompt_func.fn)
            ctx_param = sig.parameters.get("ctx")
            assert ctx_param is not None, f"{prompt_func.fn.__name__} missing ctx parameter"
            assert ctx_param.kind == inspect.Parameter.KEYWORD_ONLY, f"{prompt_func.fn.__name__} ctx should be keyword-only"