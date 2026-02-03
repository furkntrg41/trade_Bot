"""
Structured Logging Configuration
==================================

Separates logs into:
- [STRATEGY]: Z-Score, signals, cointegration updates
- [EXECUTION]: Order placement, fills, hedging
- [SAFETY]: Rollbacks, protection triggers, errors

Usage:
    from scripts.logging_config import get_logger
    
    strategy_logger = get_logger("STRATEGY")
    execution_logger = get_logger("EXECUTION")
    safety_logger = get_logger("SAFETY")

Author: DevOps Team
Date: 2026-02-01
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    COLORS = {
        "STRATEGY": "\033[94m",      # Blue
        "EXECUTION": "\033[92m",     # Green
        "SAFETY": "\033[91m",        # Red
        "DEFAULT": "\033[0m",        # Reset
    }
    
    def format(self, record):
        category = getattr(record, "category", "DEFAULT")
        color = self.COLORS.get(category, self.COLORS["DEFAULT"])
        reset = "\033[0m"
        
        # Format: [CATEGORY] timestamp - level: message
        record.msg = f"{color}[{category}]{reset} {record.msg}"
        return super().format(record)


def get_logger(category: str) -> logging.Logger:
    """
    Get a category-specific logger
    
    Args:
        category: One of "STRATEGY", "EXECUTION", "SAFETY"
    
    Returns:
        Configured logger with category tag
    """
    logger = logging.getLogger(f"freqtrade.{category.lower()}")
    logger.setLevel(logging.INFO)
    
    # Add category attribute
    for handler in logger.handlers:
        if not isinstance(handler, logging.NullHandler):
            return logger
    
    # Create handlers if not exist
    log_dir = Path("/freqtrade/user_data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = StructuredFormatter(
        fmt="%(asctime)s - %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    
    # File handler (category-specific)
    file_handler = logging.FileHandler(
        log_dir / f"{category.lower()}.log",
        mode="a",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Add category to all records
    def add_category(record):
        record.category = category
        return True
    
    logger.addFilter(logging.Filter.addFilter)
    
    return logger


# Pre-create loggers
STRATEGY = get_logger("STRATEGY")
EXECUTION = get_logger("EXECUTION")
SAFETY = get_logger("SAFETY")


def log_strategy_signal(pair_id: str, zscore: float, threshold: float, signal_type: str):
    """Log strategy signal"""
    STRATEGY.info(
        f"Signal #{pair_id:>10} | Z-Score: {zscore:>7.3f} | "
        f"Threshold: {threshold:>5.2f} | Type: {signal_type:>6}"
    )


def log_cointegration_update(pair_id: str, coint_stat: float, pvalue: float):
    """Log cointegration test result"""
    STRATEGY.info(
        f"Cointegration #{pair_id:>10} | "
        f"Stat: {coint_stat:>8.3f} | P-value: {pvalue:>8.6f}"
    )


def log_order_placement(symbol: str, side: str, amount: float, price: float, order_id: str):
    """Log order placement"""
    EXECUTION.info(
        f"Order Placed | {symbol:>12} | {side:>5} | "
        f"Amount: {amount:>10.4f} @ {price:>10.2f} | ID: {order_id}"
    )


def log_order_fill(symbol: str, side: str, amount: float, price: float, fill_ratio: float):
    """Log order fill"""
    EXECUTION.info(
        f"Order Fill   | {symbol:>12} | {side:>5} | "
        f"Amount: {amount:>10.4f} @ {price:>10.2f} | Fill: {fill_ratio*100:>5.1f}%"
    )


def log_hedging_update(leg_a: str, leg_b: str, ratio_a: float, ratio_b: float):
    """Log dynamic hedging adjustment"""
    EXECUTION.info(
        f"Hedging Update | {leg_a:>6} ↔ {leg_b:>6} | "
        f"Ratio A: {ratio_a:>8.4f} | Ratio B: {ratio_b:>8.4f}"
    )


def log_safety_trigger(reason: str, details: str):
    """Log safety trigger event"""
    SAFETY.warning(
        f"Safety Trigger | {reason:>20} | {details}"
    )


def log_rollback(trade_id: str, reason: str, unwind_status: str):
    """Log trade rollback"""
    SAFETY.warning(
        f"Trade Rollback | ID: {trade_id:>10} | "
        f"Reason: {reason:>20} | Status: {unwind_status}"
    )


def log_crash_recovery(orphaned_positions: int, orphaned_orders: int):
    """Log crash recovery result"""
    SAFETY.info(
        f"Crash Recovery Complete | "
        f"Orphaned Positions: {orphaned_positions} | "
        f"Orphaned Orders: {orphaned_orders}"
    )
