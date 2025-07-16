"""
MCP-native OAuth consent tool for eBay user authorization.

Handles user consent flow for APIs requiring user tokens (Account).
Provides an MCP-native experience without web redirects.
"""
import os
import json
import uuid
import aiohttp
import sys
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from fastmcp import Context
from pydantic import BaseModel, Field, ConfigDict

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


class UserTokenData(BaseModel):
    """User token storage model."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    access_token: str = Field(..., description="User access token")
    refresh_token: str = Field(..., description="User refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_at: datetime = Field(..., description="Token expiration time")
    scope: str = Field(..., description="Granted scopes")
    user_id: Optional[str] = Field(None, description="eBay user ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Token creation time")


class TokenStorage:
    """Secure token storage manager."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize token storage."""
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            # Default to ~/.ebay/oauth_tokens.json
            self.storage_path = Path.home() / ".ebay" / "oauth_tokens.json"
        
        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set secure permissions (readable only by owner)
        if self.storage_path.exists():
            os.chmod(self.storage_path, 0o600)
    
    def store_user_token(self, token_data: UserTokenData, app_id: str) -> None:
        """Store user token securely."""
        # Load existing tokens
        tokens = self._load_tokens()
        
        # Store token under app_id key
        tokens[app_id] = {
            "access_token": token_data.access_token,
            "refresh_token": token_data.refresh_token,
            "token_type": token_data.token_type,
            "expires_at": token_data.expires_at.isoformat(),
            "scope": token_data.scope,
            "user_id": token_data.user_id,
            "created_at": token_data.created_at.isoformat()
        }
        
        # Save tokens
        self._save_tokens(tokens)
    
    def get_user_token(self, app_id: str) -> Optional[UserTokenData]:
        """Retrieve user token for app."""
        tokens = self._load_tokens()
        
        if app_id not in tokens:
            return None
        
        token_data = tokens[app_id]
        
        try:
            return UserTokenData(
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=datetime.fromisoformat(token_data["expires_at"]),
                scope=token_data["scope"],
                user_id=token_data.get("user_id"),
                created_at=datetime.fromisoformat(token_data["created_at"])
            )
        except (KeyError, ValueError) as e:
            # Invalid token data, remove it
            del tokens[app_id]
            self._save_tokens(tokens)
            return None
    
    def delete_user_token(self, app_id: str) -> bool:
        """Delete user token for app."""
        tokens = self._load_tokens()
        
        if app_id in tokens:
            del tokens[app_id]
            self._save_tokens(tokens)
            return True
        
        return False
    
    def _load_tokens(self) -> Dict[str, Any]:
        """Load tokens from storage."""
        if not self.storage_path.exists():
            return {}
        
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save_tokens(self, tokens: Dict[str, Any]) -> None:
        """Save tokens to storage."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            # Ensure secure permissions
            os.chmod(self.storage_path, 0o600)
        except IOError as e:
            raise Exception(f"Failed to save tokens: {e}")


# Global token storage instance
_token_storage = TokenStorage()


def _can_open_browser() -> bool:
    """Check if we can open a browser (running in stdio mode)."""
    # Check if we're running in a terminal/stdio environment
    # This is a simple heuristic - in practice, MCP servers running locally
    # through stdio can often open browsers
    return sys.stdin.isatty() and sys.stdout.isatty()


def _open_browser(url: str) -> bool:
    """Open URL in the default browser if possible."""
    if not _can_open_browser():
        return False
    
    try:
        return webbrowser.open(url)
    except Exception:
        return False


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
    await ctx.info("Checking user consent status...")
    
    if not mcp.config.app_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID not configured"
        ).to_json_string()
    
    # Check if user token exists and is valid
    user_token = _token_storage.get_user_token(mcp.config.app_id)
    
    if not user_token:
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
    if user_token.expires_at <= datetime.now(timezone.utc):
        return success_response(
            data={
                "has_consent": False,
                "consent_required": True,
                "consent_expired": True,
                "expired_at": user_token.expires_at.isoformat(),
                "required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split(),
                "message": "User consent expired, re-authorization required"
            },
            message="User consent expired"
        ).to_json_string()
    
    # Valid consent exists
    granted_scopes = user_token.scope.split()
    required_scopes = OAuthScopes.USER_CONSENT_SCOPES.split()
    
    return success_response(
        data={
            "has_consent": True,
            "consent_required": False,
            "user_id": user_token.user_id,
            "granted_scopes": granted_scopes,
            "required_scopes": required_scopes,
            "expires_at": user_token.expires_at.isoformat(),
            "created_at": user_token.created_at.isoformat(),
            "token_type": user_token.token_type
        },
        message="User consent is valid"
    ).to_json_string()


@mcp.tool
async def initiate_user_consent(ctx: Context) -> str:
    """
    Initiate the user consent flow for eBay APIs.
    
    Generates authorization URL and provides instructions for user consent.
    This is the first step in the OAuth authorization code flow.
    
    Args:
        ctx: MCP context
    
    Returns:
        JSON response with authorization URL and instructions
    """
    await ctx.info("Initiating user consent flow...")
    
    # Check configuration
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
        ).to_json_string()
    
    # Generate state parameter for security
    state = str(uuid.uuid4())
    
    # Build authorization URL
    base_url = "https://auth.sandbox.ebay.com/oauth2/authorize" if mcp.config.sandbox_mode else "https://auth.ebay.com/oauth2/authorize"
    
    # Use redirect URI from environment or default to RuName
    # eBay uses RuName as redirect URI for some apps
    redirect_uri = os.getenv("EBAY_REDIRECT_URI", "Travis_Melhiser-TravisMe-Lootly-menhqo")
    await ctx.info(f"Using redirect URI: {redirect_uri}")
    
    # URL encode parameters
    from urllib.parse import urlencode
    
    params = {
        "client_id": mcp.config.app_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": OAuthScopes.USER_CONSENT_SCOPES,
        "state": state
    }
    
    auth_url = f"{base_url}?{urlencode(params)}"
    
    # Store state for validation (in memory for this session)
    # In production, you'd want to store this more persistently
    ctx.session_data = getattr(ctx, 'session_data', {})
    ctx.session_data['oauth_state'] = state
    ctx.session_data['oauth_redirect_uri'] = redirect_uri
    
    # Provide user instructions
    instructions = [
        "Click the authorization URL to open eBay's consent page",
        "Log in to your eBay account and grant the requested permissions",
        "After granting consent, you'll be redirected to localhost (this will show an error page - this is normal)",
        "Copy the ENTIRE URL from your browser's address bar",
        "Paste the URL back in this console when prompted"
    ]
    
    required_scopes = [
        {
            "scope": OAuthScopes.SELL_ACCOUNT,
            "description": "Manage seller account settings and policies"
        }
    ]
    
    await ctx.info(f"Authorization URL generated. State: {state}")
    
    # Try to open browser automatically if running locally
    browser_opened = _open_browser(auth_url)
    
    if browser_opened:
        await ctx.info("🌐 Browser opened automatically! Complete authorization in the browser window.")
        browser_status = "Browser opened automatically"
    else:
        await ctx.info("🔗 Copy the authorization URL below and open it in your browser.")
        browser_status = "Browser not opened - copy URL manually"
    
    return success_response(
        data={
            "authorization_url": auth_url,
            "state": state,
            "redirect_uri": redirect_uri,
            "required_scopes": required_scopes,
            "instructions": instructions,
            "expires_in": 600,  # URL expires in 10 minutes
            "environment": "sandbox" if mcp.config.sandbox_mode else "production",
            "browser_opened": browser_opened,
            "browser_status": browser_status,
            "next_step": "Use complete_user_consent with the callback URL after authorization"
        },
        message=f"✅ User consent initiated. {browser_status}. Complete authorization and then use complete_user_consent with the callback URL."
    ).to_json_string()


@mcp.tool
async def complete_user_consent(
    ctx: Context,
    callback_url: str
) -> str:
    """
    Complete the user consent flow using the callback URL.
    
    Exchanges the authorization code for user tokens and stores them securely.
    
    Args:
        callback_url: The full URL copied from browser after consent
        ctx: MCP context
    
    Returns:
        JSON response with consent completion status
    """
    await ctx.info("Completing user consent flow...")
    await ctx.report_progress(0.1, "Validating callback URL...")
    
    # Check configuration
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
        ).to_json_string()
    
    # Parse callback URL
    try:
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(callback_url)
        query_params = parse_qs(parsed_url.query)
        
        # Extract authorization code
        if 'code' not in query_params:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                "Authorization code not found in callback URL"
            ).to_json_string()
        
        auth_code = query_params['code'][0]
        
        # Validate state parameter
        if 'state' in query_params:
            received_state = query_params['state'][0]
            session_data = getattr(ctx, 'session_data', {})
            expected_state = session_data.get('oauth_state')
            
            if received_state != expected_state:
                return error_response(
                    ErrorCode.VALIDATION_ERROR,
                    "State parameter mismatch - possible CSRF attack"
                ).to_json_string()
        
        # Get redirect URI from session
        session_data = getattr(ctx, 'session_data', {})
        redirect_uri = session_data.get('oauth_redirect_uri', "https://localhost")
        
    except Exception as e:
        await ctx.error(f"Failed to parse callback URL: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid callback URL: {str(e)}"
        ).to_json_string()
    
    # Initialize OAuth manager
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id,
        sandbox=mcp.config.sandbox_mode,
        redirect_uri=redirect_uri
    )
    oauth_manager = OAuthManager(oauth_config)
    
    try:
        await ctx.report_progress(0.3, "Exchanging authorization code for tokens...")
        
        # Exchange authorization code for tokens
        token_response = await oauth_manager.exchange_code_for_tokens(auth_code, redirect_uri)
        
        await ctx.report_progress(0.8, "Storing user tokens...")
        
        # Create user token data
        expires_in = token_response.get("expires_in", 7200)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        user_token = UserTokenData(
            access_token=token_response["access_token"],
            refresh_token=token_response.get("refresh_token", ""),
            token_type=token_response.get("token_type", "Bearer"),
            expires_at=expires_at,
            scope=token_response.get("scope", OAuthScopes.USER_CONSENT_SCOPES)
        )
        
        # Store token securely
        _token_storage.store_user_token(user_token, mcp.config.app_id)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info("User consent completed successfully")
        
        return success_response(
            data={
                "consent_granted": True,
                "user_id": user_token.user_id,
                "granted_scopes": user_token.scope.split(),
                "expires_at": user_token.expires_at.isoformat(),
                "token_type": user_token.token_type,
                "has_refresh_token": bool(user_token.refresh_token),
                "message": "User consent granted successfully. You can now use Account API."
            },
            message="User consent completed successfully"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Failed to complete consent: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            f"Failed to complete user consent: {str(e)}"
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
    await ctx.info("Revoking user consent...")
    
    if not mcp.config.app_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID not configured"
        ).to_json_string()
    
    # Delete stored tokens
    deleted = _token_storage.delete_user_token(mcp.config.app_id)
    
    if deleted:
        await ctx.info("User consent revoked successfully")
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


async def get_user_access_token(app_id: str) -> Optional[str]:
    """
    Get valid user access token for API calls.
    
    This function is used by other APIs to get user tokens.
    Handles token refresh if needed.
    
    Args:
        app_id: eBay application ID
        
    Returns:
        Valid user access token or None if not available
    """
    user_token = _token_storage.get_user_token(app_id)
    
    if not user_token:
        return None
    
    # Check if token is expired
    if user_token.expires_at <= datetime.now(timezone.utc):
        # TODO: Implement token refresh logic
        # For now, return None to indicate consent is needed
        return None
    
    return user_token.access_token


