"""
Parquet Schema Definitions for Historical Data.

Defines standard schemas for:
- Index/Stock OHLCV data
- Options chain snapshots
- IV history tracking
"""

from typing import Dict, Any, List
import pandas as pd


# OHLCV Schema for Index and Stock data
OHLCV_SCHEMA = {
    'columns': {
        'timestamp': {
            'type': 'datetime64[ns]',
            'required': True,
            'description': 'Candle timestamp'
        },
        'open': {
            'type': 'float64',
            'required': True,
            'description': 'Opening price'
        },
        'high': {
            'type': 'float64',
            'required': True,
            'description': 'High price (must be >= open, close, low)'
        },
        'low': {
            'type': 'float64',
            'required': True,
            'description': 'Low price (must be <= open, close, high)'
        },
        'close': {
            'type': 'float64',
            'required': True,
            'description': 'Closing price'
        },
        'volume': {
            'type': 'int64',
            'required': False,
            'default': 0,
            'description': 'Trading volume'
        },
        'open_interest': {
            'type': 'int64',
            'required': False,
            'default': 0,
            'description': 'Open interest (for derivatives)'
        }
    },
    'primary_key': ['timestamp'],
    'validation_rules': [
        'high >= low',
        'high >= open',
        'high >= close',
        'low <= open',
        'low <= close',
        'volume >= 0',
        'open_interest >= 0'
    ]
}


# Option Chain Schema
OPTION_CHAIN_SCHEMA = {
    'columns': {
        'timestamp': {
            'type': 'datetime64[ns]',
            'required': True,
            'description': 'Snapshot timestamp'
        },
        'underlying_symbol': {
            'type': 'string',
            'required': True,
            'description': 'Underlying instrument (e.g., NSE_INDEX|Nifty 50)'
        },
        'underlying_spot': {
            'type': 'float64',
            'required': True,
            'description': 'Spot price of underlying'
        },
        'expiry_date': {
            'type': 'datetime64[ns]',
            'required': True,
            'description': 'Option expiry date'
        },
        'strike_price': {
            'type': 'float64',
            'required': True,
            'description': 'Strike price'
        },
        'option_type': {
            'type': 'string',
            'required': True,
            'description': 'Option type: CE or PE',
            'enum': ['CE', 'PE']
        },
        'ltp': {
            'type': 'float64',
            'required': True,
            'description': 'Last traded price'
        },
        'bid_price': {
            'type': 'float64',
            'required': False,
            'default': 0.0,
            'description': 'Best bid price'
        },
        'bid_qty': {
            'type': 'int64',
            'required': False,
            'default': 0,
            'description': 'Best bid quantity'
        },
        'ask_price': {
            'type': 'float64',
            'required': False,
            'default': 0.0,
            'description': 'Best ask price'
        },
        'ask_qty': {
            'type': 'int64',
            'required': False,
            'default': 0,
            'description': 'Best ask quantity'
        },
        'oi': {
            'type': 'int64',
            'required': False,
            'default': 0,
            'description': 'Open interest'
        },
        'oi_change': {
            'type': 'int64',
            'required': False,
            'default': 0,
            'description': 'Change in open interest'
        },
        'volume': {
            'type': 'int64',
            'required': False,
            'default': 0,
            'description': 'Trading volume'
        },
        'iv': {
            'type': 'float64',
            'required': False,
            'default': 0.0,
            'description': 'Implied volatility (%)'
        },
        'delta': {
            'type': 'float64',
            'required': False,
            'default': 0.0,
            'description': 'Delta (-1 to 1)'
        },
        'gamma': {
            'type': 'float64',
            'required': False,
            'default': 0.0,
            'description': 'Gamma'
        },
        'theta': {
            'type': 'float64',
            'required': False,
            'default': 0.0,
            'description': 'Theta (daily time decay)'
        },
        'vega': {
            'type': 'float64',
            'required': False,
            'default': 0.0,
            'description': 'Vega'
        },
        'iv_rank': {
            'type': 'float64',
            'required': False,
            'default': None,
            'description': 'IV Rank (0-100%)'
        },
        'iv_percentile': {
            'type': 'float64',
            'required': False,
            'default': None,
            'description': 'IV Percentile (0-100%)'
        }
    },
    'primary_key': ['timestamp', 'underlying_symbol', 'expiry_date', 'strike_price', 'option_type'],
    'validation_rules': [
        'strike_price > 0',
        'ltp >= 0',
        'iv >= 0',
        'delta >= -1 AND delta <= 1',
        'oi >= 0',
        'volume >= 0'
    ]
}


# IV History Schema
IV_HISTORY_SCHEMA = {
    'columns': {
        'date': {
            'type': 'datetime64[ns]',
            'required': True,
            'description': 'Date of observation'
        },
        'underlying': {
            'type': 'string',
            'required': True,
            'description': 'Underlying symbol'
        },
        'atm_iv': {
            'type': 'float64',
            'required': True,
            'description': 'ATM implied volatility (%)'
        },
        'spot_price': {
            'type': 'float64',
            'required': False,
            'default': 0.0,
            'description': 'Spot price at observation'
        }
    },
    'primary_key': ['date', 'underlying'],
    'validation_rules': [
        'atm_iv >= 0',
        'spot_price >= 0'
    ]
}


def validate_ohlcv_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate OHLCV DataFrame against schema.

    Args:
        df: DataFrame to validate

    Returns:
        Dictionary with validation results
    """
    issues = []

    # Check required columns
    required_cols = [
        col for col, spec in OHLCV_SCHEMA['columns'].items()
        if spec.get('required', False)
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        issues.append({
            'type': 'missing_columns',
            'columns': missing
        })

    if len(df) == 0:
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'row_count': 0
        }

    # Check OHLC relationships
    invalid_ohlc = df[
        (df['high'] < df['low']) |
        (df['high'] < df['close']) |
        (df['high'] < df['open']) |
        (df['low'] > df['close']) |
        (df['low'] > df['open'])
    ]
    if len(invalid_ohlc) > 0:
        issues.append({
            'type': 'invalid_ohlc',
            'count': len(invalid_ohlc),
            'sample_indices': list(invalid_ohlc.index[:5])
        })

    # Check for negative values
    for col in ['volume', 'open_interest']:
        if col in df.columns:
            negative = df[df[col] < 0]
            if len(negative) > 0:
                issues.append({
                    'type': f'negative_{col}',
                    'count': len(negative)
                })

    # Check for duplicates
    if 'timestamp' in df.columns:
        duplicates = df[df.duplicated(subset=['timestamp'], keep=False)]
        if len(duplicates) > 0:
            issues.append({
                'type': 'duplicate_timestamps',
                'count': len(duplicates)
            })

    # Check for nulls in required columns
    for col in required_cols:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                issues.append({
                    'type': 'null_values',
                    'column': col,
                    'count': int(null_count)
                })

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'row_count': len(df)
    }


def validate_option_chain_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate option chain DataFrame against schema.

    Args:
        df: DataFrame to validate

    Returns:
        Dictionary with validation results
    """
    issues = []

    # Check required columns
    required_cols = [
        col for col, spec in OPTION_CHAIN_SCHEMA['columns'].items()
        if spec.get('required', False)
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        issues.append({
            'type': 'missing_columns',
            'columns': missing
        })

    if len(df) == 0:
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'row_count': 0
        }

    # Check option_type values
    if 'option_type' in df.columns:
        invalid_types = df[~df['option_type'].isin(['CE', 'PE'])]
        if len(invalid_types) > 0:
            issues.append({
                'type': 'invalid_option_type',
                'count': len(invalid_types)
            })

    # Check strike price is positive
    if 'strike_price' in df.columns:
        invalid_strikes = df[df['strike_price'] <= 0]
        if len(invalid_strikes) > 0:
            issues.append({
                'type': 'invalid_strike_price',
                'count': len(invalid_strikes)
            })

    # Check delta range
    if 'delta' in df.columns:
        invalid_delta = df[(df['delta'] < -1) | (df['delta'] > 1)]
        if len(invalid_delta) > 0:
            issues.append({
                'type': 'invalid_delta',
                'count': len(invalid_delta)
            })

    # Check IV is non-negative
    if 'iv' in df.columns:
        invalid_iv = df[df['iv'] < 0]
        if len(invalid_iv) > 0:
            issues.append({
                'type': 'negative_iv',
                'count': len(invalid_iv)
            })

    # Check for duplicates
    pk_cols = ['timestamp', 'underlying_symbol', 'expiry_date', 'strike_price', 'option_type']
    available_pk = [col for col in pk_cols if col in df.columns]
    if len(available_pk) == len(pk_cols):
        duplicates = df[df.duplicated(subset=available_pk, keep=False)]
        if len(duplicates) > 0:
            issues.append({
                'type': 'duplicate_rows',
                'count': len(duplicates)
            })

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'row_count': len(df),
        'strikes': df['strike_price'].nunique() if 'strike_price' in df.columns else 0,
        'option_types': df['option_type'].unique().tolist() if 'option_type' in df.columns else []
    }


def get_schema_columns(schema_name: str) -> List[str]:
    """
    Get list of columns for a schema.

    Args:
        schema_name: 'ohlcv', 'option_chain', or 'iv_history'

    Returns:
        List of column names
    """
    schemas = {
        'ohlcv': OHLCV_SCHEMA,
        'option_chain': OPTION_CHAIN_SCHEMA,
        'iv_history': IV_HISTORY_SCHEMA
    }

    schema = schemas.get(schema_name.lower())
    if schema is None:
        raise ValueError(f"Unknown schema: {schema_name}")

    return list(schema['columns'].keys())


def get_required_columns(schema_name: str) -> List[str]:
    """
    Get list of required columns for a schema.

    Args:
        schema_name: 'ohlcv', 'option_chain', or 'iv_history'

    Returns:
        List of required column names
    """
    schemas = {
        'ohlcv': OHLCV_SCHEMA,
        'option_chain': OPTION_CHAIN_SCHEMA,
        'iv_history': IV_HISTORY_SCHEMA
    }

    schema = schemas.get(schema_name.lower())
    if schema is None:
        raise ValueError(f"Unknown schema: {schema_name}")

    return [
        col for col, spec in schema['columns'].items()
        if spec.get('required', False)
    ]
