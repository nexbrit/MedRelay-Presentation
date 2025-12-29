"""
Professional Terminal Dashboard UI using Rich library

Single-screen trading command center with:
- Account summary
- Active positions
- Live signals
- Alerts/Warnings
- Market regime indicator
- Performance metrics
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.columns import Columns
from rich.progress import Progress, BarColumn, TextColumn
from datetime import datetime
from typing import Dict, List, Optional
import time


class TerminalDashboard:
    """
    Terminal-based trading dashboard using Rich library

    Features:
    - Real-time account summary
    - Active positions table
    - Live market signals
    - Risk metrics
    - Alerts and warnings
    - Market regime display
    """

    def __init__(self):
        """Initialize terminal dashboard"""
        self.console = Console()
        self.layout = Layout()

        # Dashboard data
        self.account_data = {}
        self.positions = []
        self.signals = []
        self.alerts = []
        self.performance = {}
        self.market_regime = "UNKNOWN"

        self._setup_layout()

    def _setup_layout(self):
        """Setup dashboard layout"""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )

        # Split body into sections
        self.layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )

        # Left column
        self.layout["left"].split(
            Layout(name="account", size=10),
            Layout(name="positions"),
        )

        # Right column
        self.layout["right"].split(
            Layout(name="signals", size=12),
            Layout(name="performance", size=10),
            Layout(name="alerts")
        )

    def set_account_data(
        self,
        capital: float,
        daily_pnl: float,
        portfolio_heat: float,
        trades_today: int,
        max_trades: int
    ):
        """Set account summary data"""
        self.account_data = {
            'capital': capital,
            'daily_pnl': daily_pnl,
            'portfolio_heat': portfolio_heat,
            'trades_today': trades_today,
            'max_trades': max_trades
        }

    def set_positions(self, positions: List[Dict]):
        """Set active positions"""
        self.positions = positions

    def set_signals(self, signals: List[Dict]):
        """Set current trading signals"""
        self.signals = signals

    def add_alert(self, message: str, level: str = "INFO"):
        """Add alert message"""
        self.alerts.append({
            'timestamp': datetime.now(),
            'message': message,
            'level': level
        })

        # Keep only last 10 alerts
        if len(self.alerts) > 10:
            self.alerts.pop(0)

    def set_performance(self, performance: Dict):
        """Set performance metrics"""
        self.performance = performance

    def set_market_regime(self, regime: str):
        """Set market regime"""
        self.market_regime = regime

    def _create_header(self) -> Panel:
        """Create header panel"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        header_text = Text()
        header_text.append("F&O TRADING DASHBOARD", style="bold white on blue")
        header_text.append(f"  |  {now}", style="dim")
        header_text.append(f"  |  Regime: {self.market_regime}", style="bold yellow")

        return Panel(header_text, style="blue")

    def _create_account_summary(self) -> Panel:
        """Create account summary panel"""
        if not self.account_data:
            return Panel("No account data available", title="Account Summary")

        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan")
        table.add_column(style="white")

        # Capital
        capital = self.account_data.get('capital', 0)
        table.add_row("💰 Capital:", f"₹{capital:,.2f}")

        # Daily P&L with color
        daily_pnl = self.account_data.get('daily_pnl', 0)
        pnl_color = "green" if daily_pnl >= 0 else "red"
        pnl_symbol = "+" if daily_pnl >= 0 else ""
        table.add_row(
            "📊 Today's P&L:",
            f"[{pnl_color}]{pnl_symbol}₹{daily_pnl:,.2f}[/{pnl_color}]"
        )

        # Portfolio heat with progress bar
        heat = self.account_data.get('portfolio_heat', 0)
        heat_color = "green" if heat < 3 else "yellow" if heat < 5 else "red"
        table.add_row(
            "🔥 Portfolio Heat:",
            f"[{heat_color}]{heat:.1f}%[/{heat_color}]"
        )

        # Trades today
        trades = self.account_data.get('trades_today', 0)
        max_trades = self.account_data.get('max_trades', 5)
        table.add_row(
            "📈 Trades Today:",
            f"{trades}/{max_trades}"
        )

        return Panel(table, title="💼 Account Summary", border_style="cyan")

    def _create_positions_table(self) -> Panel:
        """Create positions table"""
        if not self.positions:
            return Panel("No open positions", title="Active Positions", border_style="yellow")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Instrument", style="cyan")
        table.add_column("Type", justify="center")
        table.add_column("Qty", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("LTP", justify="right")
        table.add_column("P&L", justify="right")

        for pos in self.positions:
            pnl = pos.get('pnl', 0)
            pnl_color = "green" if pnl >= 0 else "red"

            table.add_row(
                pos.get('instrument', 'N/A'),
                pos.get('type', 'N/A'),
                str(pos.get('quantity', 0)),
                f"₹{pos.get('entry_price', 0):.2f}",
                f"₹{pos.get('ltp', 0):.2f}",
                f"[{pnl_color}]₹{pnl:,.2f}[/{pnl_color}]"
            )

        return Panel(table, title="📋 Active Positions", border_style="yellow")

    def _create_signals_panel(self) -> Panel:
        """Create signals panel"""
        if not self.signals:
            return Panel("No signals available", title="Live Signals", border_style="green")

        table = Table(show_header=True, header_style="bold green")
        table.add_column("Instrument", style="cyan")
        table.add_column("Signal", justify="center")
        table.add_column("Strength", justify="center")
        table.add_column("Price", justify="right")

        for signal in self.signals[:5]:  # Show top 5
            signal_type = signal.get('signal', 'HOLD')

            # Color code signals
            if signal_type == 'STRONG_BUY':
                signal_style = "bold green"
                emoji = "🚀"
            elif signal_type == 'BUY':
                signal_style = "green"
                emoji = "📈"
            elif signal_type == 'STRONG_SELL':
                signal_style = "bold red"
                emoji = "⬇️"
            elif signal_type == 'SELL':
                signal_style = "red"
                emoji = "📉"
            else:
                signal_style = "yellow"
                emoji = "⏸️"

            table.add_row(
                signal.get('instrument', 'N/A'),
                f"[{signal_style}]{emoji} {signal_type}[/{signal_style}]",
                str(signal.get('strength', 0)),
                f"₹{signal.get('price', 0):.2f}"
            )

        return Panel(table, title="🎯 Live Signals", border_style="green")

    def _create_performance_panel(self) -> Panel:
        """Create performance metrics panel"""
        if not self.performance:
            return Panel("No performance data", title="Performance", border_style="blue")

        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan")
        table.add_column(style="white")

        # Win rate with color
        win_rate = self.performance.get('win_rate', 0)
        wr_color = "green" if win_rate >= 50 else "yellow" if win_rate >= 40 else "red"
        table.add_row("Win Rate:", f"[{wr_color}]{win_rate:.1f}%[/{wr_color}]")

        # Profit factor
        pf = self.performance.get('profit_factor', 0)
        pf_color = "green" if pf >= 1.5 else "yellow" if pf >= 1.0 else "red"
        table.add_row("Profit Factor:", f"[{pf_color}]{pf:.2f}[/{pf_color}]")

        # Sharpe ratio
        sharpe = self.performance.get('sharpe_ratio', 0)
        table.add_row("Sharpe Ratio:", f"{sharpe:.2f}")

        # Max drawdown
        max_dd = self.performance.get('max_drawdown', 0)
        dd_color = "green" if max_dd < 5 else "yellow" if max_dd < 10 else "red"
        table.add_row("Max Drawdown:", f"[{dd_color}]{max_dd:.1f}%[/{dd_color}]")

        return Panel(table, title="📊 Performance", border_style="blue")

    def _create_alerts_panel(self) -> Panel:
        """Create alerts panel"""
        if not self.alerts:
            return Panel("No alerts", title="Alerts", border_style="red")

        alert_texts = []

        for alert in reversed(self.alerts[-5:]):  # Show last 5
            level = alert.get('level', 'INFO')
            message = alert.get('message', '')
            timestamp = alert.get('timestamp', datetime.now())

            # Color code by level
            if level == "ERROR" or level == "CRITICAL":
                style = "bold red"
                emoji = "🚨"
            elif level == "WARNING":
                style = "yellow"
                emoji = "⚠️"
            else:
                style = "white"
                emoji = "ℹ️"

            time_str = timestamp.strftime("%H:%M:%S")
            alert_texts.append(f"[{style}]{emoji} {time_str} - {message}[/{style}]")

        content = "\n".join(alert_texts)

        return Panel(content, title="🔔 Alerts", border_style="red")

    def _create_footer(self) -> Panel:
        """Create footer panel"""
        footer_text = Text()
        footer_text.append("Press Ctrl+C to exit", style="dim")
        footer_text.append(" | ", style="dim")
        footer_text.append("Last updated: ", style="dim")
        footer_text.append(datetime.now().strftime("%H:%M:%S"), style="white")

        return Panel(footer_text, style="dim")

    def render(self):
        """Render dashboard once"""
        self.layout["header"].update(self._create_header())
        self.layout["account"].update(self._create_account_summary())
        self.layout["positions"].update(self._create_positions_table())
        self.layout["signals"].update(self._create_signals_panel())
        self.layout["performance"].update(self._create_performance_panel())
        self.layout["alerts"].update(self._create_alerts_panel())
        self.layout["footer"].update(self._create_footer())

        self.console.print(self.layout)

    def render_live(self, update_function, interval: int = 1):
        """
        Render dashboard with live updates

        Args:
            update_function: Function to call for updates
            interval: Update interval in seconds
        """
        with Live(self.layout, console=self.console, refresh_per_second=1) as live:
            while True:
                try:
                    # Call update function
                    update_function()

                    # Update layout
                    self.layout["header"].update(self._create_header())
                    self.layout["account"].update(self._create_account_summary())
                    self.layout["positions"].update(self._create_positions_table())
                    self.layout["signals"].update(self._create_signals_panel())
                    self.layout["performance"].update(self._create_performance_panel())
                    self.layout["alerts"].update(self._create_alerts_panel())
                    self.layout["footer"].update(self._create_footer())

                    time.sleep(interval)

                except KeyboardInterrupt:
                    break

    def clear(self):
        """Clear console"""
        self.console.clear()

    def print_banner(self):
        """Print welcome banner"""
        banner = """
        ╔═══════════════════════════════════════════════════════════╗
        ║                                                           ║
        ║        F&O PROFESSIONAL TRADING PLATFORM                  ║
        ║        Terminal Dashboard v1.0                            ║
        ║                                                           ║
        ║        Risk Management • Analytics • Live Signals         ║
        ║                                                           ║
        ╚═══════════════════════════════════════════════════════════╝
        """

        self.console.print(banner, style="bold cyan")

    def print_quick_stats(
        self,
        capital: float,
        daily_pnl: float,
        win_rate: float,
        trades_today: int
    ):
        """Print quick stats summary"""
        table = Table(title="Quick Stats", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Capital", f"₹{capital:,.2f}")

        pnl_color = "green" if daily_pnl >= 0 else "red"
        pnl_symbol = "+" if daily_pnl >= 0 else ""
        table.add_row("Today's P&L", f"[{pnl_color}]{pnl_symbol}₹{daily_pnl:,.2f}[/{pnl_color}]")

        wr_color = "green" if win_rate >= 50 else "yellow"
        table.add_row("Win Rate", f"[{wr_color}]{win_rate:.1f}%[/{wr_color}]")

        table.add_row("Trades Today", str(trades_today))

        self.console.print(table)

    def show_error(self, message: str):
        """Show error message"""
        self.console.print(f"\n[bold red]❌ Error:[/bold red] {message}\n")

    def show_success(self, message: str):
        """Show success message"""
        self.console.print(f"\n[bold green]✅ Success:[/bold green] {message}\n")

    def show_warning(self, message: str):
        """Show warning message"""
        self.console.print(f"\n[bold yellow]⚠️  Warning:[/bold yellow] {message}\n")

    def show_info(self, message: str):
        """Show info message"""
        self.console.print(f"\n[bold blue]ℹ️  Info:[/bold blue] {message}\n")


# Example usage
if __name__ == "__main__":
    # Demo dashboard
    dashboard = TerminalDashboard()

    dashboard.print_banner()

    # Set demo data
    dashboard.set_account_data(
        capital=100000,
        daily_pnl=2500,
        portfolio_heat=3.5,
        trades_today=3,
        max_trades=5
    )

    dashboard.set_positions([
        {
            'instrument': 'NIFTY 24000 CE',
            'type': 'LONG',
            'quantity': 50,
            'entry_price': 250,
            'ltp': 275,
            'pnl': 1250
        },
        {
            'instrument': 'BANKNIFTY 47000 PE',
            'type': 'SHORT',
            'quantity': 25,
            'entry_price': 180,
            'ltp': 160,
            'pnl': 500
        }
    ])

    dashboard.set_signals([
        {'instrument': 'NIFTY', 'signal': 'STRONG_BUY', 'strength': 8, 'price': 23950},
        {'instrument': 'BANKNIFTY', 'signal': 'HOLD', 'strength': 5, 'price': 47200},
        {'instrument': 'FINNIFTY', 'signal': 'SELL', 'strength': 6, 'price': 21500},
    ])

    dashboard.set_performance({
        'win_rate': 65.5,
        'profit_factor': 1.85,
        'sharpe_ratio': 1.42,
        'max_drawdown': 4.2
    })

    dashboard.set_market_regime("STRONG_UPTREND")

    dashboard.add_alert("NIFTY showing strong bullish momentum", "INFO")
    dashboard.add_alert("Portfolio heat approaching 4%", "WARNING")

    # Render once
    dashboard.render()
