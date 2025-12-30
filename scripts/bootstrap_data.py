#!/usr/bin/env python3
"""
Data Bootstrap Script - Download initial historical data for backtesting.

This script downloads and stores historical data required for:
- Backtesting trading strategies
- Analyzing historical IV patterns
- Training and validating models

Usage:
    python scripts/bootstrap_data.py --help
    python scripts/bootstrap_data.py --indices --days 365
    python scripts/bootstrap_data.py --options --days 30

Requirements:
    - Valid Upstox API credentials configured
    - Sufficient API rate limit quota (250 requests/min)

Note: Historical options data is only available for recent dates.
Full historical option chain data requires daily snapshots over time.
"""

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.downloaders.historical_downloader import (  # noqa: E402
    HistoricalDownloader,
    DataInterval,
    DownloadStatus,
)
from data.downloaders.options_chain_downloader import OptionsChainDownloader  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default instruments to download
DEFAULT_INDICES = [
    'NSE_INDEX|Nifty 50',
    'NSE_INDEX|Nifty Bank',
    'NSE_INDEX|Nifty IT',
    'NSE_INDEX|Nifty Financial Services',
    'NSE_INDEX|India VIX',
]

# Common F&O stocks
DEFAULT_STOCKS = [
    'NSE_EQ|RELIANCE',
    'NSE_EQ|TCS',
    'NSE_EQ|HDFCBANK',
    'NSE_EQ|INFY',
    'NSE_EQ|ICICIBANK',
    'NSE_EQ|SBIN',
    'NSE_EQ|BHARTIARTL',
    'NSE_EQ|ITC',
    'NSE_EQ|KOTAKBANK',
    'NSE_EQ|LT',
]

# Intervals to download for indices (most useful for F&O)
INDEX_INTERVALS = [
    DataInterval.MINUTE_15,
    DataInterval.DAY,
]

# Intervals to download for stocks
STOCK_INTERVALS = [
    DataInterval.DAY,
]


def get_upcoming_expiries(underlying: str, count: int = 4) -> List[date]:
    """
    Get upcoming expiry dates for an underlying.

    For Nifty/BankNifty: Weekly expiry on Thursday
    For other indices/stocks: Monthly expiry on last Thursday

    Args:
        underlying: Underlying instrument key
        count: Number of expiries to return

    Returns:
        List of expiry dates
    """
    expiries = []
    current = date.today()

    # Determine if weekly or monthly expiry
    is_weekly = 'Nifty 50' in underlying or 'Nifty Bank' in underlying

    if is_weekly:
        # Find next Thursday
        days_until_thursday = (3 - current.weekday()) % 7
        if days_until_thursday == 0 and current.weekday() == 3:
            # If today is Thursday, include it
            next_expiry = current
        else:
            next_expiry = current + timedelta(days=days_until_thursday)

        for _ in range(count):
            expiries.append(next_expiry)
            next_expiry += timedelta(days=7)
    else:
        # Monthly: Find last Thursday of each month
        month = current.month
        year = current.year

        for _ in range(count):
            # Find last Thursday of this month
            # Start from day 28 and work forward to find last Thursday
            last_day = date(year, month, 28)
            while True:
                try:
                    last_day = date(year, month, last_day.day + 1)
                except ValueError:
                    break

            # Find the last Thursday
            while last_day.weekday() != 3:  # 3 = Thursday
                last_day -= timedelta(days=1)

            if last_day >= current:
                expiries.append(last_day)

            # Move to next month
            month += 1
            if month > 12:
                month = 1
                year += 1

        # Ensure we have enough expiries
        while len(expiries) < count:
            # Find last Thursday of this month
            last_day = date(year, month, 28)
            while True:
                try:
                    last_day = date(year, month, last_day.day + 1)
                except ValueError:
                    break

            while last_day.weekday() != 3:
                last_day -= timedelta(days=1)

            expiries.append(last_day)
            month += 1
            if month > 12:
                month = 1
                year += 1

    return expiries[:count]


def download_index_data(
    downloader: HistoricalDownloader,
    indices: List[str],
    days: int,
    intervals: List[DataInterval]
) -> dict:
    """
    Download historical data for indices.

    Args:
        downloader: HistoricalDownloader instance
        indices: List of index instrument keys
        days: Number of days of history
        intervals: List of intervals to download

    Returns:
        Summary of download results
    """
    results = {'success': 0, 'partial': 0, 'failed': 0, 'skipped': 0}
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    logger.info(f"Downloading index data from {start_date} to {end_date}")

    for index in indices:
        for interval in intervals:
            logger.info(f"Downloading {index} @ {interval.value}...")

            result = downloader.download_index_history(
                index, start_date, end_date, interval
            )

            status = result['status']
            if status == DownloadStatus.SUCCESS:
                results['success'] += 1
                logger.info(f"  ✓ Downloaded {result.get('records', 0)} records")
            elif status == DownloadStatus.PARTIAL:
                results['partial'] += 1
                logger.warning(f"  ~ Partial download: {result.get('message', '')}")
            elif status == DownloadStatus.SKIPPED:
                results['skipped'] += 1
                logger.info("  - Skipped (already exists)")
            else:
                results['failed'] += 1
                logger.error(f"  ✗ Failed: {result.get('message', '')}")

    return results


def download_stock_data(
    downloader: HistoricalDownloader,
    stocks: List[str],
    days: int,
    intervals: List[DataInterval]
) -> dict:
    """
    Download historical data for stocks.

    Args:
        downloader: HistoricalDownloader instance
        stocks: List of stock instrument keys
        days: Number of days of history
        intervals: List of intervals to download

    Returns:
        Summary of download results
    """
    results = {'success': 0, 'partial': 0, 'failed': 0, 'skipped': 0}
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    logger.info(f"Downloading stock data from {start_date} to {end_date}")

    for stock in stocks:
        for interval in intervals:
            logger.info(f"Downloading {stock} @ {interval.value}...")

            result = downloader.download_equity_history(
                stock, start_date, end_date, interval
            )

            status = result['status']
            if status == DownloadStatus.SUCCESS:
                results['success'] += 1
                logger.info(f"  ✓ Downloaded {result.get('records', 0)} records")
            elif status == DownloadStatus.PARTIAL:
                results['partial'] += 1
                logger.warning(f"  ~ Partial download: {result.get('message', '')}")
            elif status == DownloadStatus.SKIPPED:
                results['skipped'] += 1
                logger.info("  - Skipped (already exists)")
            else:
                results['failed'] += 1
                logger.error(f"  ✗ Failed: {result.get('message', '')}")

    return results


def download_option_chains(
    downloader: OptionsChainDownloader,
    underlyings: List[str],
    expiry_count: int = 2
) -> dict:
    """
    Download current option chain snapshots.

    Note: Historical option chain data is NOT available via API.
    This downloads current snapshots only. Build historical data
    by running this script daily.

    Args:
        downloader: OptionsChainDownloader instance
        underlyings: List of underlying instrument keys
        expiry_count: Number of expiries to download

    Returns:
        Summary of download results
    """
    results = {'success': 0, 'failed': 0, 'skipped': 0}
    today = date.today()

    logger.info("Downloading option chain snapshots (current date only)")
    logger.warning(
        "Note: Historical option chain data is not available via API. "
        "Run this script daily to build historical snapshots."
    )

    for underlying in underlyings:
        expiries = get_upcoming_expiries(underlying, expiry_count)

        for expiry in expiries:
            logger.info(f"Downloading {underlying} expiry {expiry}...")

            result = downloader.download_option_chain_snapshot(
                underlying, expiry, today
            )

            status = result.get('status', 'failed')
            if status == 'success':
                results['success'] += 1
                logger.info(f"  ✓ Downloaded {result.get('records', 0)} strikes")
            elif status == 'skipped':
                results['skipped'] += 1
                logger.info("  - Skipped (already exists)")
            else:
                results['failed'] += 1
                logger.error(f"  ✗ Failed: {result.get('message', '')}")

    return results


def print_summary(
    index_results: Optional[dict],
    stock_results: Optional[dict],
    options_results: Optional[dict]
) -> None:
    """Print download summary."""
    print("\n" + "=" * 50)
    print("DOWNLOAD SUMMARY")
    print("=" * 50)

    if index_results:
        print("\nIndex Data:")
        print(f"  Success: {index_results['success']}")
        print(f"  Partial: {index_results['partial']}")
        print(f"  Failed:  {index_results['failed']}")
        print(f"  Skipped: {index_results['skipped']}")

    if stock_results:
        print("\nStock Data:")
        print(f"  Success: {stock_results['success']}")
        print(f"  Partial: {stock_results['partial']}")
        print(f"  Failed:  {stock_results['failed']}")
        print(f"  Skipped: {stock_results['skipped']}")

    if options_results:
        print("\nOption Chains:")
        print(f"  Success: {options_results['success']}")
        print(f"  Failed:  {options_results['failed']}")
        print(f"  Skipped: {options_results['skipped']}")

    print("\n" + "=" * 50)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Download historical market data for backtesting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Download 1 year of index data
    python scripts/bootstrap_data.py --indices --days 365

    # Download stock data for F&O stocks
    python scripts/bootstrap_data.py --stocks --days 365

    # Download current option chain snapshots
    python scripts/bootstrap_data.py --options

    # Download everything with custom path
    python scripts/bootstrap_data.py --all --days 365 --data-path ./my_data

Data Limitations:
    - Intraday data: Limited to recent months (API restriction)
    - Daily data: Available for longer periods
    - Option chains: Only current snapshots available via API
    - Historical option chains must be built by running daily snapshots
        """
    )

    parser.add_argument(
        '--indices', action='store_true',
        help='Download index data (Nifty, BankNifty, etc.)'
    )
    parser.add_argument(
        '--stocks', action='store_true',
        help='Download stock data for common F&O stocks'
    )
    parser.add_argument(
        '--options', action='store_true',
        help='Download current option chain snapshots'
    )
    parser.add_argument(
        '--all', action='store_true',
        help='Download all data types'
    )
    parser.add_argument(
        '--days', type=int, default=365,
        help='Number of days of historical data (default: 365)'
    )
    parser.add_argument(
        '--data-path', type=str, default='data/historical',
        help='Base path for data storage (default: data/historical)'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be downloaded without downloading'
    )

    args = parser.parse_args()

    # If no specific option, show help
    if not (args.indices or args.stocks or args.options or args.all):
        parser.print_help()
        sys.exit(1)

    # Set flags
    download_indices = args.indices or args.all
    download_stocks = args.stocks or args.all
    download_options = args.options or args.all

    # Show dry run info
    if args.dry_run:
        print("DRY RUN - No data will be downloaded\n")

        if download_indices:
            print("Would download index data for:")
            for idx in DEFAULT_INDICES:
                print(f"  - {idx}")
            print(f"  Intervals: {[i.value for i in INDEX_INTERVALS]}")
            print(f"  Days: {args.days}")

        if download_stocks:
            print("\nWould download stock data for:")
            for stock in DEFAULT_STOCKS:
                print(f"  - {stock}")
            print(f"  Intervals: {[i.value for i in STOCK_INTERVALS]}")
            print(f"  Days: {args.days}")

        if download_options:
            print("\nWould download option chains for:")
            for idx in DEFAULT_INDICES[:2]:  # Only Nifty and BankNifty
                print(f"  - {idx}")

        sys.exit(0)

    # Initialize downloaders (without actual client for now)
    # In production, pass the authenticated Upstox client
    data_path = Path(args.data_path)

    logger.info(f"Data will be stored in: {data_path.absolute()}")

    # Note: In production, initialize with actual Upstox client
    # For now, create downloaders that will attempt API calls
    try:
        historical_downloader = HistoricalDownloader(
            upstox_client=None,  # Will use mock/demo data or fail gracefully
            data_path=data_path
        )
        options_downloader = OptionsChainDownloader(
            upstox_client=None,
            data_path=data_path / "options"
        )
    except Exception as e:
        logger.error(f"Failed to initialize downloaders: {e}")
        logger.info("Make sure Upstox credentials are configured.")
        sys.exit(1)

    # Download data
    index_results = None
    stock_results = None
    options_results = None

    try:
        if download_indices:
            index_results = download_index_data(
                historical_downloader,
                DEFAULT_INDICES,
                args.days,
                INDEX_INTERVALS
            )

        if download_stocks:
            stock_results = download_stock_data(
                historical_downloader,
                DEFAULT_STOCKS,
                args.days,
                STOCK_INTERVALS
            )

        if download_options:
            options_results = download_option_chains(
                options_downloader,
                DEFAULT_INDICES[:2],  # Only Nifty and BankNifty for options
                expiry_count=2
            )

        print_summary(index_results, stock_results, options_results)

    except KeyboardInterrupt:
        logger.info("\nDownload interrupted by user")
        print_summary(index_results, stock_results, options_results)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Download failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
