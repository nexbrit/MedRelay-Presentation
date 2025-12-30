"""
TradeFlow Theme Configuration

Professional color scheme and styling for the F&O trading dashboard.
Based on Phase 4.1 requirements from DEVELOPMENT_ROADMAP.md.
"""

# Color Palette
COLORS = {
    # Background colors
    'bg_primary': '#0f172a',      # Dark Navy
    'bg_secondary': '#1e293b',    # Slate
    'bg_accent': '#334155',       # Lighter Slate
    'bg_card': '#1e293b',         # Card background

    # Text colors
    'text_primary': '#f1f5f9',    # Light
    'text_secondary': '#94a3b8',  # Muted
    'text_muted': '#64748b',      # More muted

    # Status colors
    'profit': '#22c55e',          # Green
    'loss': '#ef4444',            # Red
    'warning': '#f59e0b',         # Amber
    'info': '#3b82f6',            # Blue
    'neutral': '#6b7280',         # Gray

    # Accent colors
    'accent_primary': '#3b82f6',  # Blue
    'accent_secondary': '#8b5cf6', # Purple

    # Border colors
    'border_light': '#334155',
    'border_dark': '#1e293b',
}

# Typography
TYPOGRAPHY = {
    'font_family': "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    'font_mono': "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",

    # Font sizes
    'h1': '2.5rem',
    'h2': '2rem',
    'h3': '1.5rem',
    'h4': '1.25rem',
    'body': '1rem',
    'small': '0.875rem',
    'tiny': '0.75rem',
}

# Component styles
COMPONENTS = {
    'border_radius': '8px',
    'border_radius_lg': '12px',
    'shadow': '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    'shadow_lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
}


def get_custom_css() -> str:
    """
    Generate custom CSS for Streamlit dashboard.

    Returns:
        CSS string to inject into Streamlit
    """
    return f"""
    <style>
    /* Global styles */
    .stApp {{
        background-color: {COLORS['bg_primary']};
    }}

    /* Main content area */
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }}

    /* Headers */
    h1, h2, h3, h4, h5, h6 {{
        color: {COLORS['text_primary']} !important;
        font-family: {TYPOGRAPHY['font_family']};
    }}

    h1 {{
        font-size: {TYPOGRAPHY['h1']} !important;
        font-weight: 700 !important;
        margin-bottom: 1.5rem !important;
    }}

    h2 {{
        font-size: {TYPOGRAPHY['h2']} !important;
        font-weight: 600 !important;
    }}

    h3 {{
        font-size: {TYPOGRAPHY['h3']} !important;
        font-weight: 600 !important;
    }}

    /* Body text */
    p, span, div {{
        color: {COLORS['text_secondary']};
    }}

    /* Metrics */
    [data-testid="stMetricValue"] {{
        font-family: {TYPOGRAPHY['font_mono']};
        font-size: 1.75rem !important;
        color: {COLORS['text_primary']} !important;
    }}

    [data-testid="stMetricDelta"] {{
        font-family: {TYPOGRAPHY['font_mono']};
    }}

    [data-testid="stMetricLabel"] {{
        color: {COLORS['text_secondary']} !important;
        font-size: {TYPOGRAPHY['small']} !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    /* Cards and containers */
    .metric-card {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border_light']};
        padding: 1.25rem;
        border-radius: {COMPONENTS['border_radius']};
        margin-bottom: 1rem;
    }}

    /* Profit/Loss styling */
    .profit {{
        color: {COLORS['profit']} !important;
    }}

    .loss {{
        color: {COLORS['loss']} !important;
    }}

    .warning {{
        color: {COLORS['warning']} !important;
    }}

    /* Connection status indicators */
    .connection-dot {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 2s infinite;
    }}

    .connected {{
        background-color: {COLORS['profit']};
        box-shadow: 0 0 8px {COLORS['profit']};
    }}

    .disconnected {{
        background-color: {COLORS['loss']};
        box-shadow: 0 0 8px {COLORS['loss']};
    }}

    .reconnecting {{
        background-color: {COLORS['warning']};
        box-shadow: 0 0 8px {COLORS['warning']};
        animation: pulse 1s infinite;
    }}

    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
    }}

    /* Token warning banners */
    .token-warning {{
        background: linear-gradient(135deg, {COLORS['warning']} 0%, #d97706 100%);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: {COMPONENTS['border_radius']};
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}

    .token-expired {{
        background: linear-gradient(135deg, {COLORS['loss']} 0%, #dc2626 100%);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: {COMPONENTS['border_radius']};
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}

    /* Market overview strip */
    .market-strip {{
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border_light']};
        border-radius: {COMPONENTS['border_radius']};
        padding: 0.75rem 1rem;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }}

    .market-item {{
        display: flex;
        flex-direction: column;
        align-items: center;
    }}

    .market-label {{
        font-size: {TYPOGRAPHY['tiny']};
        color: {COLORS['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    .market-value {{
        font-size: 1.125rem;
        font-weight: 600;
        font-family: {TYPOGRAPHY['font_mono']};
        color: {COLORS['text_primary']};
    }}

    .market-change {{
        font-size: {TYPOGRAPHY['small']};
        font-family: {TYPOGRAPHY['font_mono']};
    }}

    .market-change.positive {{
        color: {COLORS['profit']};
    }}

    .market-change.negative {{
        color: {COLORS['loss']};
    }}

    /* Account summary card */
    .account-card {{
        background: linear-gradient(135deg, {COLORS['bg_secondary']} 0%, {COLORS['bg_accent']} 100%);
        border: 1px solid {COLORS['border_light']};
        border-radius: {COMPONENTS['border_radius_lg']};
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }}

    .account-capital {{
        font-size: 2.5rem;
        font-weight: 700;
        font-family: {TYPOGRAPHY['font_mono']};
        color: {COLORS['text_primary']};
    }}

    .account-label {{
        font-size: {TYPOGRAPHY['small']};
        color: {COLORS['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    /* Portfolio heat gauge */
    .heat-gauge {{
        height: 8px;
        background: {COLORS['bg_accent']};
        border-radius: 4px;
        overflow: hidden;
        margin-top: 0.5rem;
    }}

    .heat-fill {{
        height: 100%;
        transition: width 0.3s ease, background-color 0.3s ease;
    }}

    .heat-safe {{ background: {COLORS['profit']}; }}
    .heat-caution {{ background: {COLORS['warning']}; }}
    .heat-danger {{ background: {COLORS['loss']}; }}

    /* Positions table enhancements */
    .positions-table {{
        width: 100%;
        border-collapse: collapse;
    }}

    .positions-table th {{
        background: {COLORS['bg_accent']};
        color: {COLORS['text_secondary']};
        font-size: {TYPOGRAPHY['small']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.75rem;
        text-align: left;
        border-bottom: 1px solid {COLORS['border_light']};
    }}

    .positions-table td {{
        padding: 0.75rem;
        border-bottom: 1px solid {COLORS['border_dark']};
        font-family: {TYPOGRAPHY['font_mono']};
        font-size: {TYPOGRAPHY['small']};
    }}

    .positions-table tr:hover {{
        background: {COLORS['bg_accent']};
    }}

    /* Badge styles */
    .badge {{
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: {TYPOGRAPHY['tiny']};
        font-weight: 500;
        text-transform: uppercase;
    }}

    .badge-ce {{
        background: rgba(59, 130, 246, 0.2);
        color: {COLORS['info']};
    }}

    .badge-pe {{
        background: rgba(239, 68, 68, 0.2);
        color: {COLORS['loss']};
    }}

    .badge-fut {{
        background: rgba(139, 92, 246, 0.2);
        color: {COLORS['accent_secondary']};
    }}

    /* Circuit breaker indicator */
    .circuit-breaker {{
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border_light']};
        border-radius: {COMPONENTS['border_radius']};
        padding: 1rem;
        margin-bottom: 1rem;
    }}

    .circuit-breaker.triggered {{
        border-color: {COLORS['loss']};
        background: rgba(239, 68, 68, 0.1);
    }}

    .circuit-breaker.warning {{
        border-color: {COLORS['warning']};
        background: rgba(245, 158, 11, 0.1);
    }}

    /* Last updated timestamp */
    .last-updated {{
        font-size: {TYPOGRAPHY['tiny']};
        color: {COLORS['text_muted']};
        text-align: right;
    }}

    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background-color: {COLORS['bg_secondary']};
    }}

    [data-testid="stSidebar"] .block-container {{
        padding-top: 2rem;
    }}

    /* Dataframe styling */
    .stDataFrame {{
        border: 1px solid {COLORS['border_light']};
        border-radius: {COMPONENTS['border_radius']};
    }}

    /* Button styling */
    .stButton > button {{
        background-color: {COLORS['accent_primary']};
        color: white;
        border: none;
        border-radius: {COMPONENTS['border_radius']};
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: background-color 0.2s ease;
    }}

    .stButton > button:hover {{
        background-color: #2563eb;
    }}

    /* Emergency button */
    .emergency-btn {{
        background: linear-gradient(135deg, {COLORS['loss']} 0%, #dc2626 100%) !important;
    }}

    .emergency-btn:hover {{
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
    }}

    /* Expander styling */
    .streamlit-expanderHeader {{
        background-color: {COLORS['bg_secondary']};
        border-radius: {COMPONENTS['border_radius']};
    }}

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.5rem;
    }}

    .stTabs [data-baseweb="tab"] {{
        background-color: {COLORS['bg_secondary']};
        border-radius: {COMPONENTS['border_radius']};
        color: {COLORS['text_secondary']};
        padding: 0.5rem 1rem;
    }}

    .stTabs [aria-selected="true"] {{
        background-color: {COLORS['accent_primary']};
        color: white;
    }}
    </style>
    """


def format_currency(value: float, prefix: str = "₹") -> str:
    """Format value as Indian currency with proper formatting."""
    if abs(value) >= 10000000:  # 1 crore
        return f"{prefix}{value/10000000:.2f} Cr"
    elif abs(value) >= 100000:  # 1 lakh
        return f"{prefix}{value/100000:.2f} L"
    elif abs(value) >= 1000:
        return f"{prefix}{value:,.0f}"
    else:
        return f"{prefix}{value:.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def get_pnl_color(value: float) -> str:
    """Get appropriate color for P&L value."""
    if value > 0:
        return COLORS['profit']
    elif value < 0:
        return COLORS['loss']
    return COLORS['neutral']


def get_heat_level(heat_pct: float) -> str:
    """Get heat level CSS class based on portfolio heat percentage."""
    if heat_pct <= 3:
        return 'heat-safe'
    elif heat_pct <= 5:
        return 'heat-caution'
    return 'heat-danger'


def render_market_strip(nifty: dict, banknifty: dict, vix: dict, market_status: str) -> str:
    """
    Render market overview strip HTML.

    Args:
        nifty: Dict with 'value' and 'change' keys
        banknifty: Dict with 'value' and 'change' keys
        vix: Dict with 'value' and 'change' keys
        market_status: Market status string (Pre-open/Open/Closed)

    Returns:
        HTML string for market strip
    """
    def change_class(change: float) -> str:
        return 'positive' if change >= 0 else 'negative'

    return f"""
    <div class="market-strip">
        <div class="market-item">
            <span class="market-label">Nifty 50</span>
            <span class="market-value">{nifty.get('value', 0):,.2f}</span>
            <span class="market-change {change_class(nifty.get('change', 0))}">
                {format_percentage(nifty.get('change', 0))}
            </span>
        </div>
        <div class="market-item">
            <span class="market-label">Bank Nifty</span>
            <span class="market-value">{banknifty.get('value', 0):,.2f}</span>
            <span class="market-change {change_class(banknifty.get('change', 0))}">
                {format_percentage(banknifty.get('change', 0))}
            </span>
        </div>
        <div class="market-item">
            <span class="market-label">India VIX</span>
            <span class="market-value">{vix.get('value', 0):.2f}</span>
            <span class="market-change {change_class(vix.get('change', 0))}">
                {format_percentage(vix.get('change', 0))}
            </span>
        </div>
        <div class="market-item">
            <span class="market-label">Market</span>
            <span class="market-value" style="font-size: 0.875rem;">{market_status}</span>
        </div>
    </div>
    """


def render_account_summary(
    capital: float,
    daily_pnl: float,
    daily_pnl_pct: float,
    positions_count: int,
    margin_used: float,
    margin_available: float,
    portfolio_heat: float
) -> str:
    """
    Render account summary card HTML.

    Returns:
        HTML string for account summary
    """
    pnl_color = get_pnl_color(daily_pnl)
    pnl_sign = "+" if daily_pnl > 0 else ""
    heat_class = get_heat_level(portfolio_heat)

    return f"""
    <div class="account-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
            <div>
                <span class="account-label">Total Capital</span>
                <div class="account-capital">{format_currency(capital)}</div>
            </div>
            <div style="text-align: right;">
                <span class="account-label">Day's P&L</span>
                <div style="font-size: 1.5rem; font-weight: 600; color: {pnl_color};">
                    {pnl_sign}{format_currency(daily_pnl)} ({format_percentage(daily_pnl_pct)})
                </div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
            <div>
                <span class="account-label">Open Positions</span>
                <div style="font-size: 1.25rem; font-weight: 600; color: #f1f5f9;">{positions_count}</div>
            </div>
            <div>
                <span class="account-label">Margin Used</span>
                <div style="font-size: 1.25rem; font-weight: 600; color: #f1f5f9;">{format_currency(margin_used)}</div>
            </div>
            <div>
                <span class="account-label">Available</span>
                <div style="font-size: 1.25rem; font-weight: 600; color: #f1f5f9;">{format_currency(margin_available)}</div>
            </div>
            <div>
                <span class="account-label">Portfolio Heat</span>
                <div style="font-size: 1.25rem; font-weight: 600; color: #f1f5f9;">{portfolio_heat:.1f}%</div>
                <div class="heat-gauge">
                    <div class="heat-fill {heat_class}" style="width: {min(portfolio_heat / 6 * 100, 100)}%;"></div>
                </div>
            </div>
        </div>
    </div>
    """


def get_option_type_badge(symbol: str) -> tuple[str, str]:
    """
    Determine option type from symbol and return badge class.

    Args:
        symbol: Trading symbol

    Returns:
        Tuple of (badge_text, badge_class)
    """
    symbol_upper = symbol.upper()
    if 'CE' in symbol_upper:
        return ('CE', 'badge-ce')
    elif 'PE' in symbol_upper:
        return ('PE', 'badge-pe')
    elif 'FUT' in symbol_upper:
        return ('FUT', 'badge-fut')
    return ('EQ', 'badge-eq')


def get_dte_style(days_to_expiry: int) -> str:
    """Get style for days to expiry indicator."""
    if days_to_expiry <= 0:
        return f"color: {COLORS['loss']}; font-weight: 700;"
    elif days_to_expiry <= 3:
        return f"color: {COLORS['warning']}; font-weight: 600;"
    return f"color: {COLORS['text_secondary']};"


def render_enhanced_positions_table(positions: list, capital: float) -> str:
    """
    Render enhanced positions table with F&O-specific columns.

    Args:
        positions: List of position dictionaries
        capital: Total capital for % calculations

    Returns:
        HTML string for positions table
    """
    if not positions:
        return """
        <div class="positions-empty">
            <p style="color: #94a3b8; text-align: center; padding: 2rem;">
                No active positions
            </p>
        </div>
        """

    rows_html = ""
    for pos in positions:
        symbol = pos.get('symbol', pos.get('instrument', 'Unknown'))
        qty = abs(pos.get('quantity', 0))
        avg_price = pos.get('average_price', 0)
        ltp = pos.get('last_price', avg_price)
        pnl = pos.get('unrealized_pnl', pos.get('pnl', 0))
        stop_loss = pos.get('stop_loss', 0)
        days_to_expiry = pos.get('days_to_expiry', 0)
        delta = pos.get('delta', 0)
        theta = pos.get('theta', 0)
        lot_size = pos.get('lot_size', 1)

        # Calculate derived values
        pnl_pct = ((ltp - avg_price) / avg_price * 100) if avg_price > 0 else 0
        position_value = qty * avg_price
        capital_risk_pct = (position_value / capital * 100) if capital > 0 else 0
        sl_distance_pct = ((ltp - stop_loss) / ltp * 100) if stop_loss > 0 and ltp > 0 else 0

        # Get badge info
        badge_text, badge_class = get_option_type_badge(symbol)

        # Colors
        pnl_color = get_pnl_color(pnl)
        ltp_color = COLORS['profit'] if ltp > avg_price else COLORS['loss'] if ltp < avg_price else COLORS['text_primary']
        dte_style = get_dte_style(days_to_expiry)

        # Direction indicator
        direction = pos.get('direction', 'LONG')
        direction_icon = "▲" if direction == 'LONG' else "▼"
        direction_color = COLORS['profit'] if direction == 'LONG' else COLORS['loss']

        # Lots display
        lots = qty // lot_size if lot_size > 0 else qty
        lots_display = f"{lots} lot{'s' if lots != 1 else ''}" if lot_size > 1 else str(qty)

        rows_html += f"""
        <tr>
            <td>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="badge {badge_class}">{badge_text}</span>
                    <span style="color: {COLORS['text_primary']}; font-weight: 500;">{symbol}</span>
                </div>
            </td>
            <td>
                <span style="color: {direction_color};">{direction_icon} {direction}</span>
            </td>
            <td>{lots_display}</td>
            <td>{format_currency(avg_price)}</td>
            <td style="color: {ltp_color}; font-weight: 500;">{format_currency(ltp)}</td>
            <td style="color: {pnl_color}; font-weight: 600;">
                {format_currency(pnl)}<br>
                <small style="opacity: 0.8;">{format_percentage(pnl_pct)}</small>
            </td>
            <td>{capital_risk_pct:.1f}%</td>
            <td>
                {format_currency(stop_loss) if stop_loss > 0 else '-'}<br>
                <small style="opacity: 0.8;">{sl_distance_pct:.1f}% away</small>
            </td>
            <td style="{dte_style}">{days_to_expiry}d</td>
            <td>
                <small>Δ {delta:.2f}</small><br>
                <small>Θ {theta:.2f}</small>
            </td>
        </tr>
        """

    return f"""
    <div class="positions-table-container">
        <table class="positions-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Qty</th>
                    <th>Avg</th>
                    <th>LTP</th>
                    <th>P&L</th>
                    <th>% Capital</th>
                    <th>Stop Loss</th>
                    <th>DTE</th>
                    <th>Greeks</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """


def render_connection_indicator(state: str, last_update: str) -> str:
    """
    Render connection status indicator.

    Args:
        state: Connection state (connected, disconnected, reconnecting)
        last_update: Last update timestamp string

    Returns:
        HTML string for connection indicator
    """
    state_lower = state.lower()
    if state_lower == 'connected':
        dot_class = 'connected'
        status_text = 'Live'
        icon = '🟢'
    elif state_lower == 'reconnecting':
        dot_class = 'reconnecting'
        status_text = 'Reconnecting...'
        icon = '🟡'
    else:
        dot_class = 'disconnected'
        status_text = 'Disconnected'
        icon = '🔴'

    return f"""
    <div class="connection-indicator">
        <span class="connection-dot {dot_class}"></span>
        <span class="connection-text">{icon} {status_text}</span>
        <span class="last-update-time">Updated: {last_update}</span>
    </div>
    """


def render_refresh_control(auto_refresh: bool = True, refresh_interval: int = 30) -> str:
    """
    Render refresh control with auto-refresh indicator.

    Args:
        auto_refresh: Whether auto-refresh is enabled
        refresh_interval: Refresh interval in seconds

    Returns:
        HTML string for refresh control
    """
    status_class = 'active' if auto_refresh else 'paused'
    status_text = f'Auto-refresh: {refresh_interval}s' if auto_refresh else 'Auto-refresh paused'

    return f"""
    <div class="refresh-control {status_class}">
        <span class="refresh-status">{status_text}</span>
        <div class="refresh-progress" style="animation-duration: {refresh_interval}s;">
            <div class="refresh-progress-bar"></div>
        </div>
    </div>
    """


def render_signal_card(
    instrument: str,
    signal: str,
    strength: int,
    price: float,
    entry: float = None,
    target: float = None,
    stop_loss: float = None,
    timestamp: str = None,
    indicators: list = None
) -> str:
    """
    Render a professional signal card.

    Args:
        instrument: Instrument name
        signal: Signal type (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
        strength: Signal strength (1-10)
        price: Current price
        entry: Entry price
        target: Target price
        stop_loss: Stop loss price
        timestamp: Signal timestamp
        indicators: List of contributing indicators

    Returns:
        HTML string for signal card
    """
    signal_colors = {
        'STRONG_BUY': (COLORS['profit'], 'rgba(34, 197, 94, 0.15)'),
        'BUY': ('#4ade80', 'rgba(74, 222, 128, 0.15)'),
        'HOLD': (COLORS['neutral'], 'rgba(107, 114, 128, 0.15)'),
        'SELL': ('#f87171', 'rgba(248, 113, 113, 0.15)'),
        'STRONG_SELL': (COLORS['loss'], 'rgba(239, 68, 68, 0.15)')
    }

    color, bg_color = signal_colors.get(signal, (COLORS['neutral'], 'rgba(107, 114, 128, 0.15)'))

    # Strength bar
    strength_pct = strength * 10

    # Risk:Reward calculation
    rr_ratio = ""
    if entry and target and stop_loss and entry > 0 and stop_loss > 0:
        risk = abs(entry - stop_loss)
        reward = abs(target - entry)
        if risk > 0:
            rr_ratio = f"1:{reward/risk:.2f}"

    # Entry/Target/SL section
    trade_details = ""
    if entry:
        trade_details = f"""
        <div class="signal-trade-details">
            <div class="trade-level entry">
                <span class="level-label">Entry</span>
                <span class="level-value">{format_currency(entry)}</span>
            </div>
            <div class="trade-level target">
                <span class="level-label">Target</span>
                <span class="level-value">{format_currency(target or 0)}</span>
            </div>
            <div class="trade-level stoploss">
                <span class="level-label">SL</span>
                <span class="level-value">{format_currency(stop_loss or 0)}</span>
            </div>
            {f'<div class="trade-level rr"><span class="level-label">R:R</span><span class="level-value">{rr_ratio}</span></div>' if rr_ratio else ''}
        </div>
        """

    # Indicators section
    indicators_html = ""
    if indicators:
        indicator_badges = " ".join(
            f'<span class="indicator-badge">{ind}</span>' for ind in indicators
        )
        indicators_html = f'<div class="signal-indicators">{indicator_badges}</div>'

    return f"""
    <div class="signal-card" style="border-left: 4px solid {color}; background: {bg_color};">
        <div class="signal-header">
            <div class="signal-instrument">{instrument}</div>
            <div class="signal-type" style="color: {color};">{signal.replace('_', ' ')}</div>
        </div>
        <div class="signal-price">{format_currency(price)}</div>
        <div class="signal-strength">
            <span class="strength-label">Confidence</span>
            <div class="strength-bar">
                <div class="strength-fill" style="width: {strength_pct}%; background: {color};"></div>
            </div>
            <span class="strength-value">{strength}/10</span>
        </div>
        {trade_details}
        {indicators_html}
        {f'<div class="signal-timestamp">{timestamp}</div>' if timestamp else ''}
    </div>
    """


def get_signal_css() -> str:
    """Get CSS for signal cards and related components."""
    return f"""
    <style>
    /* Signal card styles */
    .signal-card {{
        background: {COLORS['bg_secondary']};
        border-radius: {COMPONENTS['border_radius']};
        padding: 1rem;
        margin-bottom: 1rem;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}

    .signal-card:hover {{
        transform: translateY(-2px);
        box-shadow: {COMPONENTS['shadow']};
    }}

    .signal-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }}

    .signal-instrument {{
        font-size: 1.125rem;
        font-weight: 600;
        color: {COLORS['text_primary']};
    }}

    .signal-type {{
        font-size: {TYPOGRAPHY['small']};
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    .signal-price {{
        font-size: 1.5rem;
        font-weight: 700;
        font-family: {TYPOGRAPHY['font_mono']};
        color: {COLORS['text_primary']};
        margin-bottom: 0.75rem;
    }}

    .signal-strength {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
    }}

    .strength-label {{
        font-size: {TYPOGRAPHY['tiny']};
        color: {COLORS['text_muted']};
        text-transform: uppercase;
        width: 70px;
    }}

    .strength-bar {{
        flex: 1;
        height: 6px;
        background: {COLORS['bg_accent']};
        border-radius: 3px;
        overflow: hidden;
    }}

    .strength-fill {{
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
    }}

    .strength-value {{
        font-size: {TYPOGRAPHY['small']};
        font-family: {TYPOGRAPHY['font_mono']};
        color: {COLORS['text_secondary']};
        width: 40px;
        text-align: right;
    }}

    .signal-trade-details {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.5rem;
        margin-bottom: 0.75rem;
        padding: 0.5rem;
        background: {COLORS['bg_accent']};
        border-radius: 4px;
    }}

    .trade-level {{
        display: flex;
        flex-direction: column;
        align-items: center;
    }}

    .level-label {{
        font-size: {TYPOGRAPHY['tiny']};
        color: {COLORS['text_muted']};
        text-transform: uppercase;
    }}

    .level-value {{
        font-size: {TYPOGRAPHY['small']};
        font-family: {TYPOGRAPHY['font_mono']};
        color: {COLORS['text_primary']};
        font-weight: 500;
    }}

    .trade-level.entry .level-value {{ color: {COLORS['info']}; }}
    .trade-level.target .level-value {{ color: {COLORS['profit']}; }}
    .trade-level.stoploss .level-value {{ color: {COLORS['loss']}; }}

    .signal-indicators {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
        margin-bottom: 0.5rem;
    }}

    .indicator-badge {{
        font-size: {TYPOGRAPHY['tiny']};
        padding: 0.125rem 0.375rem;
        background: {COLORS['bg_accent']};
        color: {COLORS['text_secondary']};
        border-radius: 3px;
    }}

    .signal-timestamp {{
        font-size: {TYPOGRAPHY['tiny']};
        color: {COLORS['text_muted']};
        text-align: right;
    }}

    /* Signal tabs */
    .signal-tabs {{
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid {COLORS['border_light']};
        padding-bottom: 0.5rem;
    }}

    .signal-tab {{
        padding: 0.5rem 1rem;
        border-radius: {COMPONENTS['border_radius']};
        background: {COLORS['bg_secondary']};
        color: {COLORS['text_secondary']};
        cursor: pointer;
        border: none;
        font-size: {TYPOGRAPHY['small']};
        transition: all 0.15s ease;
    }}

    .signal-tab.active {{
        background: {COLORS['accent_primary']};
        color: white;
    }}

    .signal-tab:hover:not(.active) {{
        background: {COLORS['bg_accent']};
    }}
    </style>
    """


def get_additional_css() -> str:
    """
    Get additional CSS for Phase 4.2.3 and 4.2.4 components.

    Returns:
        CSS string
    """
    return f"""
    <style>
    /* Enhanced positions table (Phase 4.2.3) */
    .positions-table-container {{
        overflow-x: auto;
        border-radius: {COMPONENTS['border_radius']};
        border: 1px solid {COLORS['border_light']};
        margin-bottom: 1rem;
    }}

    .positions-table {{
        width: 100%;
        border-collapse: collapse;
        min-width: 900px;
    }}

    .positions-table th {{
        background: {COLORS['bg_accent']};
        color: {COLORS['text_secondary']};
        font-size: {TYPOGRAPHY['tiny']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.75rem 0.5rem;
        text-align: left;
        border-bottom: 2px solid {COLORS['border_light']};
        position: sticky;
        top: 0;
        white-space: nowrap;
    }}

    .positions-table td {{
        padding: 0.75rem 0.5rem;
        border-bottom: 1px solid {COLORS['border_dark']};
        font-family: {TYPOGRAPHY['font_mono']};
        font-size: {TYPOGRAPHY['small']};
        color: {COLORS['text_primary']};
        vertical-align: middle;
    }}

    .positions-table tbody tr {{
        transition: background-color 0.15s ease;
    }}

    .positions-table tbody tr:hover {{
        background: {COLORS['bg_accent']};
    }}

    /* Badge for EQ type */
    .badge-eq {{
        background: rgba(107, 114, 128, 0.2);
        color: {COLORS['neutral']};
    }}

    /* Connection indicator (Phase 4.2.4) */
    .connection-indicator {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border_light']};
        border-radius: {COMPONENTS['border_radius']};
        font-size: {TYPOGRAPHY['small']};
    }}

    .connection-text {{
        color: {COLORS['text_primary']};
        font-weight: 500;
    }}

    .last-update-time {{
        color: {COLORS['text_muted']};
        font-size: {TYPOGRAPHY['tiny']};
        margin-left: auto;
    }}

    /* Refresh control */
    .refresh-control {{
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.5rem 1rem;
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border_light']};
        border-radius: {COMPONENTS['border_radius']};
    }}

    .refresh-status {{
        font-size: {TYPOGRAPHY['small']};
        color: {COLORS['text_secondary']};
    }}

    .refresh-control.active .refresh-status {{
        color: {COLORS['profit']};
    }}

    .refresh-control.paused .refresh-status {{
        color: {COLORS['warning']};
    }}

    .refresh-progress {{
        flex: 1;
        height: 4px;
        background: {COLORS['bg_accent']};
        border-radius: 2px;
        overflow: hidden;
    }}

    .refresh-progress-bar {{
        height: 100%;
        background: {COLORS['accent_primary']};
        animation: refreshProgress linear infinite;
        width: 0%;
    }}

    .refresh-control.paused .refresh-progress-bar {{
        animation-play-state: paused;
    }}

    @keyframes refreshProgress {{
        0% {{ width: 0%; }}
        100% {{ width: 100%; }}
    }}

    /* Price change blink effect */
    .price-changed {{
        animation: priceBlink 0.5s ease-out;
    }}

    .price-up {{
        animation: priceUp 0.5s ease-out;
    }}

    .price-down {{
        animation: priceDown 0.5s ease-out;
    }}

    @keyframes priceBlink {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
    }}

    @keyframes priceUp {{
        0% {{ background-color: rgba(34, 197, 94, 0.3); }}
        100% {{ background-color: transparent; }}
    }}

    @keyframes priceDown {{
        0% {{ background-color: rgba(239, 68, 68, 0.3); }}
        100% {{ background-color: transparent; }}
    }}

    /* Position row urgent (near expiry) */
    .positions-table tr.near-expiry {{
        background: rgba(245, 158, 11, 0.1);
        border-left: 3px solid {COLORS['warning']};
    }}

    .positions-table tr.expiry-today {{
        background: rgba(239, 68, 68, 0.1);
        border-left: 3px solid {COLORS['loss']};
    }}
    </style>
    """
