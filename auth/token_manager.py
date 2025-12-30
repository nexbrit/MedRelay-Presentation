"""
Token Manager for authentication and session management.

Handles secure token storage, expiry tracking, and authentication state
management for Upstox API integration.
"""

import os
import base64
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import logging

from data.persistence.state_manager import StateManager

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages authentication tokens with secure storage and expiry tracking.

    Features:
    - Secure token storage (obfuscated)
    - Token expiry tracking and warnings
    - Automatic expiry detection
    - Re-authentication flow support
    - Multiple broker support

    Example:
        token_mgr = TokenManager()
        token_mgr.store_token(access_token, expiry_hours=24)

        if token_mgr.is_token_expired():
            # Trigger re-auth flow
            pass

        token = token_mgr.get_token()
    """

    # Upstox tokens expire in 24 hours (end of day typically)
    DEFAULT_EXPIRY_HOURS = 24
    WARNING_THRESHOLD_HOURS = 2
    CRITICAL_THRESHOLD_MINUTES = 30

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        broker: str = 'upstox'
    ):
        """
        Initialize token manager.

        Args:
            state_manager: Optional state manager for persistence
            broker: Broker identifier (default: 'upstox')
        """
        self._state = state_manager or StateManager()
        self._broker = broker
        self._token_cache: Optional[str] = None
        self._expiry_cache: Optional[datetime] = None

    def store_token(
        self,
        access_token: str,
        expiry_time: datetime = None,
        expiry_hours: float = None
    ) -> bool:
        """
        Store authentication token securely.

        Args:
            access_token: OAuth access token
            expiry_time: Token expiry datetime
            expiry_hours: Hours until expiry (used if expiry_time not provided)

        Returns:
            True if stored successfully
        """
        if not access_token:
            raise ValueError("Access token cannot be empty")

        # Calculate expiry
        if expiry_time is None:
            hours = expiry_hours or self.DEFAULT_EXPIRY_HOURS
            expiry_time = datetime.now() + timedelta(hours=hours)

        # Obfuscate token for storage (basic protection)
        obfuscated = self._obfuscate(access_token)

        # Store in state manager
        success = self._state.store_token(
            access_token=obfuscated,
            token_expiry=expiry_time,
            broker=self._broker
        )

        if success:
            # Update local cache
            self._token_cache = access_token
            self._expiry_cache = expiry_time
            logger.info(
                f"Token stored for {self._broker}, expires: {expiry_time}"
            )

        return success

    def get_token(self) -> Optional[str]:
        """
        Retrieve stored token if valid.

        Returns:
            Access token string or None if expired/not found
        """
        # Check cache first
        if self._token_cache and self._expiry_cache:
            if self._expiry_cache > datetime.now():
                return self._token_cache

        # Load from storage
        state = self._state.get_token_state()

        if not state or not state.get('access_token'):
            logger.debug("No stored token found")
            return None

        # Check expiry
        expiry = state.get('token_expiry')
        if expiry and isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry)

        if expiry and expiry <= datetime.now():
            logger.warning("Stored token has expired")
            return None

        # Deobfuscate and cache
        token = self._deobfuscate(state['access_token'])
        self._token_cache = token
        self._expiry_cache = expiry

        return token

    def is_token_valid(self) -> bool:
        """
        Check if a valid (non-expired) token exists.

        Returns:
            True if valid token exists
        """
        return self.get_token() is not None

    def is_token_expired(self) -> bool:
        """
        Check if token is expired.

        Returns:
            True if expired or no token exists
        """
        state = self._state.get_token_state()

        if not state:
            return True

        expiry = state.get('token_expiry')
        if not expiry:
            return True

        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry)

        return expiry <= datetime.now()

    def get_time_until_expiry(self) -> Optional[timedelta]:
        """
        Get time remaining until token expires.

        Returns:
            Timedelta until expiry or None if no token
        """
        state = self._state.get_token_state()

        if not state:
            return None

        expiry = state.get('token_expiry')
        if not expiry:
            return None

        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry)

        remaining = expiry - datetime.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def get_expiry_status(self) -> Dict[str, Any]:
        """
        Get comprehensive expiry status.

        Returns:
            Dictionary with expiry details and warnings
        """
        state = self._state.get_token_state()

        if not state:
            return {
                'has_token': False,
                'is_expired': True,
                'status': 'NO_TOKEN',
                'message': 'No authentication token found',
                'requires_action': True
            }

        expiry = state.get('token_expiry')
        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry)

        if not expiry:
            return {
                'has_token': True,
                'is_expired': True,
                'status': 'UNKNOWN_EXPIRY',
                'message': 'Token expiry unknown',
                'requires_action': True
            }

        now = datetime.now()
        remaining = expiry - now

        if remaining.total_seconds() <= 0:
            return {
                'has_token': True,
                'is_expired': True,
                'status': 'EXPIRED',
                'expiry_time': expiry.isoformat(),
                'message': 'Token has expired. Re-authentication required.',
                'requires_action': True
            }

        hours_remaining = remaining.total_seconds() / 3600
        minutes_remaining = remaining.total_seconds() / 60

        if minutes_remaining <= self.CRITICAL_THRESHOLD_MINUTES:
            status = 'CRITICAL'
            message = f'Token expires in {int(minutes_remaining)} minutes! Re-authenticate now.'
        elif hours_remaining <= self.WARNING_THRESHOLD_HOURS:
            status = 'WARNING'
            message = f'Token expires in {hours_remaining:.1f} hours. Consider re-authenticating soon.'
        else:
            status = 'VALID'
            message = f'Token valid for {hours_remaining:.1f} hours'

        return {
            'has_token': True,
            'is_expired': False,
            'status': status,
            'expiry_time': expiry.isoformat(),
            'time_remaining': str(remaining),
            'hours_remaining': round(hours_remaining, 2),
            'minutes_remaining': round(minutes_remaining, 0),
            'message': message,
            'requires_action': status in ['EXPIRED', 'CRITICAL'],
            'last_authenticated': state.get('last_authenticated')
        }

    def clear_token(self) -> bool:
        """
        Clear stored token (logout).

        Returns:
            True if cleared
        """
        self._token_cache = None
        self._expiry_cache = None

        # Store empty token
        return self._state.store_token(
            access_token='',
            token_expiry=datetime.now() - timedelta(days=1),
            broker=self._broker
        )

    def get_authorization_info(self) -> Dict[str, Any]:
        """
        Get information needed for re-authorization.

        Returns:
            Dictionary with auth info
        """
        api_key = os.getenv('UPSTOX_API_KEY', '')
        redirect_uri = os.getenv('UPSTOX_REDIRECT_URI', 'http://localhost:8080')

        auth_url = (
            f"https://api-v2.upstox.com/login/authorization/dialog"
            f"?response_type=code"
            f"&client_id={api_key}"
            f"&redirect_uri={redirect_uri}"
        )

        return {
            'broker': self._broker,
            'authorization_url': auth_url,
            'redirect_uri': redirect_uri,
            'has_credentials': bool(api_key),
            'current_status': self.get_expiry_status()
        }

    def _obfuscate(self, token: str) -> str:
        """
        Basic obfuscation for token storage.

        Note: This is NOT encryption, just basic protection against
        casual inspection. For production, use proper encryption.
        """
        # Simple base64 encoding with a twist
        encoded = base64.b64encode(token.encode()).decode()
        # Reverse and add marker
        return f"OBF:{encoded[::-1]}"

    def _deobfuscate(self, obfuscated: str) -> str:
        """Reverse the obfuscation."""
        if not obfuscated:
            return ''

        if obfuscated.startswith('OBF:'):
            encoded = obfuscated[4:][::-1]
            try:
                return base64.b64decode(encoded.encode()).decode()
            except Exception:
                return obfuscated
        return obfuscated

    def should_show_warning(self) -> bool:
        """
        Check if a warning should be shown to the user.

        Returns:
            True if warning banner should be displayed
        """
        status = self.get_expiry_status()
        return status.get('status') in ['WARNING', 'CRITICAL', 'EXPIRED']

    def should_block_trading(self) -> bool:
        """
        Check if trading should be blocked due to auth issues.

        Returns:
            True if trading should be blocked
        """
        status = self.get_expiry_status()
        return status.get('status') in ['EXPIRED', 'NO_TOKEN']

    def format_expiry_countdown(self) -> str:
        """
        Format expiry time as a countdown string.

        Returns:
            Human-readable countdown string
        """
        remaining = self.get_time_until_expiry()

        if remaining is None:
            return "No token"

        if remaining.total_seconds() <= 0:
            return "Expired"

        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def update_last_validated(self) -> bool:
        """
        Update the last validation timestamp.

        Call this after successful API calls to track token health.

        Returns:
            True if updated
        """
        state = self._state.get_token_state()

        if not state:
            return False

        # Re-store with updated validation time
        return self._state.store_token(
            access_token=state['access_token'],
            token_expiry=state['token_expiry'],
            broker=self._broker
        )
