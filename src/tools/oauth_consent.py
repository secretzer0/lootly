"""
MCP-native OAuth consent tool for eBay user authorization.

Handles user consent flow for APIs requiring user tokens (Account).
Provides an MCP-native experience without web redirects.
"""
from typing import Optional
from datetime import datetime, timezone
from fastmcp import Context

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.errors import EbayApiError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


@mcp.tool
async def check_user_consent_status(ctx: Context) -> str:
    """
    Check if user has already provided OAuth consent.
    
    Checks if valid user tokens exist for the current application.
    
    Args:
        ctx: MCP context
    
    Returns:
        JSON response with consent status
    """
    await ctx.info("🔍 Checking user consent status...")
    
    if not mcp.config.app_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID not configured"
        ).to_json_string()
    
    # Initialize OAuth manager
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id,
        sandbox=mcp.config.sandbox_mode
    )
    oauth_manager = OAuthManager(oauth_config)
    
    # Check if user token exists and is valid
    user_token_info = oauth_manager.get_user_token_info()
    
    if not user_token_info:
        return success_response(
            data={
                "has_consent": False,
                "consent_required": True,
                "required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split(),
                "message": "User consent required for Account API"
            },
            message="User consent required"
        ).to_json_string()
    
    # Check if token is expired
    if user_token_info.expires_at <= datetime.now(timezone.utc):
        return success_response(
            data={
                "has_consent": False,
                "consent_required": True,
                "consent_expired": True,
                "expired_at": user_token_info.expires_at.isoformat(),
                "required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split(),
                "message": "User consent expired, re-authorization required"
            },
            message="User consent expired"
        ).to_json_string()
    
    # Valid consent exists
    granted_scopes = user_token_info.scope.split()
    return success_response(
        data={
            "has_consent": True,
            "consent_required": False,
            "expires_at": user_token_info.expires_at.isoformat(),
            "granted_scopes": granted_scopes,
            "user_id": user_token_info.user_id,
            "created_at": user_token_info.created_at.isoformat(),
            "message": "Valid user consent found"
        },
        message="User consent is valid"
    ).to_json_string()


@mcp.tool
async def initiate_user_consent(ctx: Context) -> str:
    """
    REQUIRED: Initiate the user consent flow for eBay APIs.
    
    When ANY eBay API returns a consent error, you MUST:
    1. Call this tool IMMEDIATELY to get the authorization URL
    2. Wait for the browser to open or show the URL to the user
    3. PROMPT the user to complete authorization and paste the callback URL
    4. Use complete_user_consent with the callback URL
    
    DO NOT try alternative approaches - OAuth is REQUIRED.
    
    Args:
        ctx: MCP context
    
    Returns:
        JSON response with authorization URL and URGENT instructions
    """
    await ctx.info("🚀 Initiating user consent flow...")
    
    # Check configuration
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
        ).to_json_string()
    
    # Initialize OAuth manager
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id,
        sandbox=mcp.config.sandbox_mode
    )
    oauth_manager = OAuthManager(oauth_config)
    
    try:
        # Start consent flow
        result = await oauth_manager.initiate_consent_flow()
        
        # Display rich instructions to user
        await ctx.info("🌐 Starting eBay OAuth consent flow...")
        
        if result["browser_opened"]:
            await ctx.info("🌐 Browser opened automatically! Complete authorization in the browser window.")
        else:
            await ctx.info("🔗 Copy the authorization URL below and open it in your browser.")
        
        await ctx.info("📋 Instructions:")
        await ctx.info("  1. Log in to your eBay account")
        await ctx.info("  2. Grant the requested permissions")
        await ctx.info("  3. You'll be redirected to localhost (error page is normal)")
        await ctx.info("  4. Copy the ENTIRE URL from your browser's address bar")
        await ctx.info("  5. Use complete_user_consent tool with that URL")
        
        # Create urgent action message for Claude
        # IMPORTANT: Keep the URL on a single line to prevent line wrapping issues
        urgent_message = (
            "🚨 ACTION REQUIRED: OAuth Authorization Needed\n\n"
            f"{'✅ Browser opened! Please check your browser window.' if result['browser_opened'] else '❌ Could not open browser automatically.'}\n\n"
            "YOU MUST NOW:\n"
            "1. Copy and open this URL in your browser:\n\n"
            f"{result['auth_url']}\n\n"
            "2. Log in to your eBay account\n"
            "3. Grant the requested permissions\n"
            "4. After granting permissions, copy the ENTIRE URL from your browser's address bar\n"
            "5. IMMEDIATELY use the 'complete_user_consent' tool with that URL\n\n"
            "⏰ This authorization expires in 5 minutes!\n\n"
            "NOTE: The authorization URL above is on a single line - copy the entire URL even if it appears wrapped in your terminal."
        )
        
        # Also create a compact URL display for easier copying
        # Break down the URL into base and parameters for display
        url_parts = result["auth_url"].split('?', 1)
        base_url = url_parts[0]
        
        return success_response(
            data={
                "authorization_url": result["auth_url"],
                "authorization_url_base": base_url,
                "browser_opened": result["browser_opened"],
                "state": result["state"],
                "redirect_uri": result["redirect_uri"],
                "required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split(),
                "expires_in": 300,  # URL expires in 5 minutes
                "environment": "sandbox" if mcp.config.sandbox_mode else "production",
                "next_step": "IMMEDIATELY copy the callback URL from your browser and use complete_user_consent tool",
                "urgent_action": urgent_message,
                "copy_tip": f"TIP: If the URL is hard to copy, try selecting from '{base_url}' to the end of the line"
            },
            message=urgent_message
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Failed to initiate consent flow: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to initiate consent flow: {str(e)}"
        ).to_json_string()


@mcp.tool
async def complete_user_consent(ctx: Context, callback_url: str) -> str:
    """
    REQUIRED STEP 2: Complete the user consent flow using the callback URL.
    
    After calling initiate_user_consent and authorizing in the browser,
    you MUST call this tool with the full callback URL.
    
    The callback URL looks like:
    http://localhost/?code=C10...&state=cd6a...
    or
    https://localhost/?code=C10...&state=cd6a...
    
    COPY THE ENTIRE URL INCLUDING ALL PARAMETERS.
    
    Args:
        callback_url: The FULL URL copied from browser after granting consent
        ctx: MCP context
    
    Returns:
        JSON response confirming successful authorization
    """
    await ctx.info("🔄 Completing user consent flow...")
    
    # Check configuration
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
        ).to_json_string()
    
    # Initialize OAuth manager
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id,
        sandbox=mcp.config.sandbox_mode
    )
    oauth_manager = OAuthManager(oauth_config)
    
    try:
        # Complete consent flow
        result = await oauth_manager.complete_consent_flow(callback_url)
        
        await ctx.info("✅ User consent completed successfully!")
        await ctx.info("🎉 You can now use all eBay Account APIs")
        
        return success_response(
            data={
                "consent_granted": True,
                "expires_at": result["expires_at"],
                "scopes": result["scopes"],
                "message": "User consent completed successfully"
            },
            message="User consent completed. All Account APIs now available."
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Failed to complete consent flow: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to complete consent flow: {str(e)}"
        ).to_json_string()


@mcp.tool
async def revoke_user_consent(ctx: Context) -> str:
    """
    Revoke user consent and delete stored tokens.
    
    Removes stored user tokens and optionally revokes them with eBay.
    
    Args:
        ctx: MCP context
    
    Returns:
        JSON response with revocation status
    """
    await ctx.info("🚫 Revoking user consent...")
    
    if not mcp.config.app_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID not configured"
        ).to_json_string()
    
    # Initialize OAuth manager
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id,
        sandbox=mcp.config.sandbox_mode
    )
    oauth_manager = OAuthManager(oauth_config)
    
    # Delete stored tokens
    deleted = oauth_manager.delete_user_token()
    
    if deleted:
        await ctx.info("✅ User consent revoked successfully")
        return success_response(
            data={
                "consent_revoked": True,
                "message": "User consent has been revoked. Account API will no longer work until consent is granted again."
            },
            message="User consent revoked"
        ).to_json_string()
    else:
        return success_response(
            data={
                "consent_revoked": False,
                "message": "No user consent found to revoke"
            },
            message="No consent to revoke"
        ).to_json_string()