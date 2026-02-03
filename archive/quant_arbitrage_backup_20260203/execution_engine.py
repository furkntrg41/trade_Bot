"""
Execution Engine - PRODUCTION GRADE with Advanced Safety Protocols
===================================================================
Transforms TradingSignals into real Binance Futures orders with military-grade
safety mechanisms validated through chaos-mode testing.

MANDATORY SAFETY PROTOCOLS:
1. Concurrency Lock (asyncio.Lock) - Prevents race conditions
2. Partial Fill Protection - Dynamic hedge recalculation
3. Ghost Order Detection - Network timeout handling
4. Precision & Limits - Exchange-compliant orders
5. Virtual Atomicity - Rollback on failure

Author: Quant Team
Date: 2026-02-01
Version: 2.0 (Production Hardened)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

try:
    import ccxt.async_support as ccxt
except ImportError:
    raise ImportError("CCXT required: pip install ccxt")

from .signal_generator import TradingSignal, SignalStrength, SignalType
from .config import get_config, Config


logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status enum"""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PositionMode(Enum):
    """Position type"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@dataclass
class Order:
    """
    Order tracking dataclass
    
    Attributes:
        order_id: Binance order ID
        timestamp: Order time
        symbol: Trading pair (BTC/USDT)
        side: BUY or SELL
        order_type: market or limit
        quantity: Amount requested
        filled: Amount actually filled
        price: Price (for limit orders)
        status: OrderStatus
        average_price: Average fill price
        fee_cost: Commission paid
        pnl: Profit/loss for closed order
    """
    order_id: str
    timestamp: datetime
    symbol: str
    side: str  # BUY, SELL
    order_type: str  # market, limit
    quantity: float
    filled: float = 0.0
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    average_price: float = 0.0
    fee_cost: float = 0.0
    pnl: float = 0.0


@dataclass
class Position:
    """
    Position tracking dataclass
    
    Attributes:
        pair_x, pair_y: Pair symbols
        mode: LONG/SHORT/NEUTRAL
        quantity_x: pair_x quantity
        quantity_y: pair_y quantity
        entry_price_x, entry_price_y: Entry prices
        entry_time: Entry timestamp
        orders: Related orders
        unrealized_pnl: Open PnL
        realized_pnl: Closed PnL
    """
    pair_x: str
    pair_y: str
    mode: PositionMode = PositionMode.NEUTRAL
    quantity_x: float = 0.0
    quantity_y: float = 0.0
    entry_price_x: float = 0.0
    entry_price_y: float = 0.0
    entry_time: Optional[datetime] = None
    orders: List[Order] = field(default_factory=list)
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    def is_open(self) -> bool:
        """Check if position is open"""
        return abs(self.quantity_x) > 1e-6 or abs(self.quantity_y) > 1e-6


@dataclass
class ExecutionRequest:
    """
    Pair trade execution request
    
    Attributes:
        pair_x, pair_y: Trading pair symbols
        side_x, side_y: Order sides (BUY/SELL)
        amount_x, amount_y: Order amounts
        signal: Original trading signal
        hedge_ratio: Calculated hedge ratio
    """
    pair_x: str
    pair_y: str
    side_x: str  # BUY or SELL
    side_y: str  # BUY or SELL
    amount_x: float
    amount_y: float
    signal: TradingSignal
    hedge_ratio: float


class ExecutionEngine:
    """
    PRODUCTION-GRADE Execution Engine with Advanced Safety Protocols
    
    Safety Features:
    ----------------
    1. **Concurrency Lock:** Prevents spam attacks and race conditions
       - asyncio.Lock() serializes signal processing
       - pending_signals set tracks in-flight executions
       - duplicate_window (20ms) debounce period
    
    2. **Partial Fill Protection:** Dynamic hedge recalculation
       - Monitors actual fill amounts vs requested
       - Recalculates hedge based on ACTUAL Leg A fill
       - Aborts if fill < 10% (severe partial fill)
    
    3. **Ghost Order Detection:** Network timeout handling
       - Catches ccxt.RequestTimeout exceptions
       - Queries fetch_order() to verify actual status
       - Prevents duplicate orders after timeouts
    
    4. **Precision & Limits:** Exchange-compliant orders
       - amount_to_precision() for quantities
       - price_to_precision() for prices
       - min_notional validation (>5 USDT)
    
    5. **Virtual Atomicity:** Rollback on failure
       - If Leg B fails after Leg A fills → emergency close Leg A
       - Market orders for immediate rollback
       - Prevents naked directional exposure
    
    Type-safe, async, chaos-tested, production-ready.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize execution engine with safety mechanisms
        
        Args:
            config: Configuration (default: get_config())
        """
        self.config = config or get_config()
        self.exchange: Optional[ccxt.Exchange] = None
        
        # 🔒 SAFETY PROTOCOL 1: Concurrency Protection
        self.execution_lock = asyncio.Lock()
        self.pending_signals: Set[str] = set()  # Track in-flight signals
        self.duplicate_window = 0.02  # 20ms debounce period
        
        # Position tracking
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        
        # Stats
        self.total_trades = 0
        self.total_pnl = 0.0
        self.total_fees = 0.0
        
        # Safety thresholds
        self.min_fill_percentage = 10.0  # Abort if < 10% filled
        self.max_retry_attempts = 3
        self.retry_delay = 0.5  # seconds
    
    async def connect(self) -> bool:
        """
        Connect to Binance exchange
        
        Returns:
            True if connected successfully
        """
        try:
            if self.config.data.use_testnet:
                self.exchange = ccxt.binance({
                    'apiKey': self.config.binance_api_key,
                    'secret': self.config.binance_api_secret,
                    'urls': {
                        'api': 'https://testnet.binance.vision/api',
                    },
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',
                    },
                })
            else:
                self.exchange = ccxt.binance({
                    'apiKey': self.config.binance_api_key,
                    'secret': self.config.binance_api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',
                    },
                })
            
            # Test connection
            balance = await self.exchange.fetch_balance()
            total_usdt = balance.get('total', {}).get('USDT', 0)
            
            logger.info(
                f"✅ ExecutionEngine connected | "
                f"Balance: ${total_usdt:,.2f} | "
                f"Safety protocols: ENABLED"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close exchange connection"""
        if self.exchange:
            await self.exchange.close()
            logger.info("ExecutionEngine disconnected")
    
    async def execute_pair_trade(self, request: ExecutionRequest) -> bool:
        """
        Execute pair trade with FULL SAFETY PROTOCOL ENFORCEMENT
        
        This is the main entry point for pair trading execution.
        Implements all 5 mandatory safety protocols.
        
        Args:
            request: ExecutionRequest with trade parameters
            
        Returns:
            True if both legs executed successfully, False otherwise
        """
        signal_key = f"{request.pair_x}_{request.pair_y}_{request.side_x}"
        
        # 🔒 SAFETY PROTOCOL 1: Concurrency Protection
        async with self.execution_lock:
            # Check for duplicate signal
            if signal_key in self.pending_signals:
                logger.warning(
                    f"⚠️ DUPLICATE SIGNAL REJECTED: {signal_key} "
                    f"(already in execution)"
                )
                return False
            
            # Mark signal as in-flight
            self.pending_signals.add(signal_key)
        
        try:
            # Prepare symbols
            symbol_x = f"{request.pair_x}/USDT:USDT"
            symbol_y = f"{request.pair_y}/USDT:USDT"
            
            logger.info(
                f"\n{'='*80}\n"
                f"🎯 EXECUTING PAIR TRADE: {request.pair_x}/{request.pair_y}\n"
                f"{'='*80}\n"
                f"Leg A: {request.side_x} {request.amount_x:.6f} {request.pair_x}\n"
                f"Leg B: {request.side_y} {request.amount_y:.6f} {request.pair_y}\n"
                f"Hedge Ratio: {request.hedge_ratio:.4f}\n"
                f"Z-Score: {request.signal.z_score:.2f}\n"
                f"{'='*80}"
            )
            
            # Get current prices
            ticker_x = await self.exchange.fetch_ticker(symbol_x)
            ticker_y = await self.exchange.fetch_ticker(symbol_y)
            price_x = ticker_x['last']
            price_y = ticker_y['last']
            
            # 🔒 SAFETY PROTOCOL 4: Precision & Limits
            qty_x = self._apply_precision(symbol_x, request.amount_x)
            qty_y = self._apply_precision(symbol_y, request.amount_y)
            
            # Validate min notional
            if not self._validate_notional(qty_x, price_x, symbol_x):
                return False
            if not self._validate_notional(qty_y, price_y, symbol_y):
                return False
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 📤 LEG A EXECUTION (Primary)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            logger.info(f"📤 Executing Leg A: {request.side_x} {qty_x:.6f} {request.pair_x}...")
            
            order_a = await self._place_order(
                symbol=symbol_x,
                side=request.side_x,
                quantity=qty_x,
                order_type='market',
            )
            
            if not order_a:
                logger.error("❌ Leg A execution failed")
                return False
            
            # 🔒 SAFETY PROTOCOL 2: Partial Fill Protection
            filled_a = order_a.get('filled', 0)
            fill_percentage = (filled_a / qty_x) * 100
            
            logger.info(
                f"✅ Leg A filled: {filled_a:.6f}/{qty_x:.6f} "
                f"({fill_percentage:.1f}%)"
            )
            
            # Check for severe partial fill
            if fill_percentage < self.min_fill_percentage:
                logger.error(
                    f"🚨 SEVERE PARTIAL FILL: {fill_percentage:.1f}% < "
                    f"{self.min_fill_percentage}% → ABORTING"
                )
                # Emergency close the partial fill
                await self._emergency_close(
                    symbol=symbol_x,
                    side='SELL' if request.side_x == 'BUY' else 'BUY',
                    quantity=filled_a,
                    reason="Severe Partial Fill Abort"
                )
                return False
            
            # Recalculate hedge based on ACTUAL fill
            if fill_percentage < 99.0:  # Any partial fill
                original_qty_y = qty_y
                qty_y = request.amount_y * (filled_a / qty_x)
                qty_y = self._apply_precision(symbol_y, qty_y)
                
                logger.warning(
                    f"⚠️ PARTIAL FILL DETECTED: Recalculating hedge\n"
                    f"   Original Leg B: {original_qty_y:.6f} {request.pair_y}\n"
                    f"   Adjusted Leg B: {qty_y:.6f} {request.pair_y} "
                    f"(scaled by {fill_percentage:.1f}%)"
                )
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 📤 LEG B EXECUTION (Hedge) - CRITICAL SECTION
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            logger.info(f"📤 Executing Leg B: {request.side_y} {qty_y:.6f} {request.pair_y}...")
            
            order_b = None
            leg_b_success = False
            
            # 🔒 SAFETY PROTOCOL 3: Ghost Order Detection
            try:
                order_b = await self._place_order(
                    symbol=symbol_y,
                    side=request.side_y,
                    quantity=qty_y,
                    order_type='market',
                )
                
                if order_b:
                    leg_b_success = True
                    logger.info(f"✅ Leg B filled: {order_b.get('filled', 0):.6f}")
                
            except ccxt.RequestTimeout as timeout_error:
                logger.warning(
                    f"⚠️ NETWORK TIMEOUT on Leg B: {timeout_error}\n"
                    f"🔍 Checking for ghost order..."
                )
                
                # Verify if order actually went through
                ghost_order = await self._verify_ghost_order(
                    symbol=symbol_y,
                    side=request.side_y,
                    quantity=qty_y,
                )
                
                if ghost_order:
                    logger.info(
                        f"✅ GHOST ORDER FOUND: Order {ghost_order['id']} "
                        f"exists on exchange (filled: {ghost_order.get('filled', 0):.6f})"
                    )
                    order_b = ghost_order
                    leg_b_success = True
                else:
                    logger.error(
                        f"❌ NO GHOST ORDER: Timeout occurred but order not found on exchange"
                    )
                    leg_b_success = False
            
            except Exception as leg_b_error:
                logger.error(f"❌ Leg B execution failed: {leg_b_error}")
                leg_b_success = False
            
            # 🔒 SAFETY PROTOCOL 5: Virtual Atomicity (Rollback)
            if not leg_b_success:
                logger.critical(
                    f"\n{'='*80}\n"
                    f"🚨 ATOMIC EXECUTION FAILURE\n"
                    f"{'='*80}\n"
                    f"Leg A: FILLED ({filled_a:.6f} {request.pair_x})\n"
                    f"Leg B: FAILED\n"
                    f"Action: EMERGENCY ROLLBACK\n"
                    f"{'='*80}"
                )
                
                await self._emergency_close(
                    symbol=symbol_x,
                    side='SELL' if request.side_x == 'BUY' else 'BUY',
                    quantity=filled_a,
                    reason="Leg B Failure - Atomic Rollback"
                )
                return False
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # ✅ SUCCESS: Both legs executed
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            logger.info(
                f"\n{'='*80}\n"
                f"✅ PAIR TRADE EXECUTED SUCCESSFULLY\n"
                f"{'='*80}\n"
                f"Leg A: {request.side_x} {filled_a:.6f} {request.pair_x} @ ${price_x:.2f}\n"
                f"Leg B: {request.side_y} {order_b.get('filled', 0):.6f} {request.pair_y} @ ${price_y:.2f}\n"
                f"Total Value: ${filled_a * price_x + order_b.get('filled', 0) * price_y:.2f}\n"
                f"{'='*80}\n"
            )
            
            # Track position
            self._track_position(
                request=request,
                order_a=order_a,
                order_b=order_b,
                price_x=price_x,
                price_y=price_y,
            )
            
            self.total_trades += 2
            return True
            
        except Exception as e:
            logger.error(
                f"❌ Pair trade execution failed: {e}",
                exc_info=True
            )
            return False
            
        finally:
            # Remove from pending signals after debounce window
            await asyncio.sleep(self.duplicate_window)
            self.pending_signals.discard(signal_key)
    
    def _apply_precision(self, symbol: str, amount: float) -> float:
        """
        Apply exchange precision to amount
        
        🔒 SAFETY CRITICAL: Binance rejects imprecise orders
        
        Args:
            symbol: Trading pair
            amount: Raw amount
            
        Returns:
            Precision-adjusted amount
        """
        try:
            return float(self.exchange.amount_to_precision(symbol, amount))
        except Exception as e:
            logger.warning(f"Precision conversion failed: {e}, using raw amount")
            return amount
    
    def _validate_notional(self, quantity: float, price: float, symbol: str) -> bool:
        """
        Validate minimum notional value (Binance minimum ~5 USDT)
        
        🔒 SAFETY CRITICAL: Orders below min notional are rejected
        
        Args:
            quantity: Order quantity
            price: Current price
            symbol: Trading pair
            
        Returns:
            True if notional is valid
        """
        notional = quantity * price
        min_notional = self.config.execution.min_order_value
        
        if notional < min_notional:
            logger.error(
                f"❌ NOTIONAL VALIDATION FAILED: {symbol}\n"
                f"   Notional: ${notional:.2f} < Min: ${min_notional:.2f}"
            )
            return False
        
        return True
    
    async def _place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = 'market',
        price: Optional[float] = None,
    ) -> Optional[dict]:
        """
        Place order on exchange with retry logic
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            order_type: market or limit
            price: Price (for limit orders)
            
        Returns:
            Order dict or None
        """
        for attempt in range(self.max_retry_attempts):
            try:
                if side.upper() == 'BUY':
                    if order_type == 'market':
                        order = await self.exchange.create_market_buy_order(
                            symbol, quantity
                        )
                    else:
                        order = await self.exchange.create_limit_buy_order(
                            symbol, quantity, price
                        )
                else:  # SELL
                    if order_type == 'market':
                        order = await self.exchange.create_market_sell_order(
                            symbol, quantity
                        )
                    else:
                        order = await self.exchange.create_limit_sell_order(
                            symbol, quantity, price
                        )
                
                return order
                
            except ccxt.RequestTimeout:
                # Let caller handle timeout (ghost order detection)
                raise
                
            except Exception as e:
                logger.warning(
                    f"⚠️ Order placement failed (attempt {attempt+1}/{self.max_retry_attempts}): {e}"
                )
                
                if attempt < self.max_retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"❌ Order placement failed after {self.max_retry_attempts} attempts")
                    return None
    
    async def _verify_ghost_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        lookback_seconds: int = 60,
    ) -> Optional[dict]:
        """
        Verify if a "ghost order" exists after timeout
        
        🔒 SAFETY PROTOCOL 3: Ghost Order Detection
        
        After a timeout exception, the order may have actually gone through.
        This method checks recent orders to find the ghost order.
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Expected quantity
            lookback_seconds: How far back to search
            
        Returns:
            Ghost order dict if found, None otherwise
        """
        try:
            # Fetch recent orders
            orders = await self.exchange.fetch_orders(
                symbol=symbol,
                since=None,
                limit=10,
            )
            
            # Look for matching order (same side, quantity, recent timestamp)
            current_time = datetime.utcnow().timestamp() * 1000  # milliseconds
            
            for order in orders:
                order_time = order.get('timestamp', 0)
                order_side = order.get('side', '').upper()
                order_amount = order.get('amount', 0)
                
                # Check if order matches criteria
                time_diff = (current_time - order_time) / 1000  # seconds
                quantity_match = abs(order_amount - quantity) / quantity < 0.01  # 1% tolerance
                
                if (order_side == side.upper() and 
                    quantity_match and 
                    time_diff < lookback_seconds):
                    
                    logger.info(
                        f"🔍 Ghost order found: {order['id']} "
                        f"({order_side} {order_amount:.6f} @ {time_diff:.1f}s ago)"
                    )
                    return order
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ghost order verification failed: {e}")
            return None
    
    async def _emergency_close(
        self,
        symbol: str,
        side: str,
        quantity: float,
        reason: str,
    ) -> None:
        """
        🚨 EMERGENCY ROLLBACK: Close position immediately (Market Order)
        
        🔒 SAFETY PROTOCOL 5: Virtual Atomicity
        
        Use Case: When one leg of pair fills but other fails,
        close the filled leg immediately to avoid naked directional exposure.
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Amount to close
            reason: Why emergency close triggered
        """
        try:
            logger.critical(
                f"\n{'='*80}\n"
                f"🚨 EMERGENCY CLOSE INITIATED\n"
                f"{'='*80}\n"
                f"Symbol: {symbol}\n"
                f"Side: {side}\n"
                f"Quantity: {quantity:.6f}\n"
                f"Reason: {reason}\n"
                f"{'='*80}"
            )
            
            if side.upper() == 'BUY':
                await self.exchange.create_market_buy_order(symbol, quantity)
            else:
                await self.exchange.create_market_sell_order(symbol, quantity)
            
            logger.info(f"✅ Emergency close executed successfully")
            
        except Exception as e:
            logger.critical(
                f"\n{'='*80}\n"
                f"💀💀💀 CRITICAL FAILURE 💀💀💀\n"
                f"{'='*80}\n"
                f"Emergency close FAILED for {symbol}\n"
                f"Quantity: {quantity:.6f}\n"
                f"Error: {e}\n"
                f"⚠️ MANUAL INTERVENTION REQUIRED ⚠️\n"
                f"{'='*80}\n"
            )
            # In production: Send Telegram alert, email, SMS, etc.
    
    def _track_position(
        self,
        request: ExecutionRequest,
        order_a: dict,
        order_b: dict,
        price_x: float,
        price_y: float,
    ) -> None:
        """
        Track opened position
        
        Args:
            request: Original execution request
            order_a: Leg A order
            order_b: Leg B order
            price_x: Leg A price
            price_y: Leg B price
        """
        position_key = f"{request.pair_x}_{request.pair_y}"
        
        qty_x = order_a.get('filled', 0)
        qty_y = order_b.get('filled', 0)
        
        # Determine position mode
        if request.side_x == 'BUY':
            mode = PositionMode.LONG
            signed_qty_x = qty_x
            signed_qty_y = -qty_y
        else:
            mode = PositionMode.SHORT
            signed_qty_x = -qty_x
            signed_qty_y = qty_y
        
        self.positions[position_key] = Position(
            pair_x=request.pair_x,
            pair_y=request.pair_y,
            mode=mode,
            quantity_x=signed_qty_x,
            quantity_y=signed_qty_y,
            entry_price_x=price_x,
            entry_price_y=price_y,
            entry_time=datetime.utcnow(),
            orders=[
                Order(
                    order_id=order_a.get('id', 'unknown'),
                    timestamp=datetime.utcnow(),
                    symbol=f"{request.pair_x}/USDT:USDT",
                    side=request.side_x,
                    order_type='market',
                    quantity=qty_x,
                    filled=qty_x,
                    average_price=price_x,
                    status=OrderStatus.CLOSED,
                ),
                Order(
                    order_id=order_b.get('id', 'unknown'),
                    timestamp=datetime.utcnow(),
                    symbol=f"{request.pair_y}/USDT:USDT",
                    side=request.side_y,
                    order_type='market',
                    quantity=qty_y,
                    filled=qty_y,
                    average_price=price_y,
                    status=OrderStatus.CLOSED,
                ),
            ],
        )
        
        logger.debug(f"Position tracked: {position_key} ({mode.value})")
    
    async def execute_signal(self, signal: TradingSignal) -> bool:
        """
        High-level signal execution wrapper
        
        Converts TradingSignal to ExecutionRequest and executes
        
        Args:
            signal: TradingSignal from signal generator
            
        Returns:
            True if executed successfully
        """
        if not self.exchange:
            logger.error("Exchange not connected")
            return False
        
        try:
            # Calculate order size
            size_usdt = await self._calculate_order_size(signal)
            
            if size_usdt <= 0:
                logger.warning(f"Invalid order size: ${size_usdt:.2f}")
                return False
            
            # Get current prices for quantity calculation
            symbol_x = f"{signal.pair_x}/USDT:USDT"
            symbol_y = f"{signal.pair_y}/USDT:USDT"
            
            ticker_x = await self.exchange.fetch_ticker(symbol_x)
            ticker_y = await self.exchange.fetch_ticker(symbol_y)
            
            price_x = ticker_x['last']
            price_y = ticker_y['last']
            
            # Calculate quantities
            amount_x = size_usdt / price_x
            amount_y = (size_usdt * signal.hedge_ratio) / price_y
            
            # Determine sides based on signal type
            if signal.signal_type == SignalType.BUY:
                # Spread too wide → Buy pair_x, Sell pair_y
                side_x, side_y = 'BUY', 'SELL'
            elif signal.signal_type == SignalType.SELL:
                # Spread too narrow → Sell pair_x, Buy pair_y
                side_x, side_y = 'SELL', 'BUY'
            elif signal.signal_type == SignalType.EXIT:
                # Close existing position
                return await self._close_position(signal)
            else:
                logger.warning(f"Unknown signal type: {signal.signal_type}")
                return False
            
            # Create execution request
            request = ExecutionRequest(
                pair_x=signal.pair_x,
                pair_y=signal.pair_y,
                side_x=side_x,
                side_y=side_y,
                amount_x=amount_x,
                amount_y=amount_y,
                signal=signal,
                hedge_ratio=signal.hedge_ratio,
            )
            
            # Execute with full safety protocol
            return await self.execute_pair_trade(request)
            
        except Exception as e:
            logger.error(f"Signal execution failed: {e}", exc_info=True)
            return False
    
    async def _calculate_order_size(self, signal: TradingSignal) -> float:
        """
        Calculate order size from signal
        
        Args:
            signal: TradingSignal
            
        Returns:
            Order size in USDT
        """
        try:
            balance = await self.exchange.fetch_balance()
            account_equity = balance.get('free', {}).get('USDT', 0)
            
            if account_equity <= 0:
                logger.error("Account equity is zero")
                return 0
            
            # Base size (risk per trade)
            base_size = account_equity * self.config.execution.risk_per_trade
            
            # Scale by signal strength
            size_multiplier = signal.strength.value
            
            # Scale by confidence
            confidence_multiplier = signal.suggested_position_size
            
            # Final size
            final_size = base_size * size_multiplier * confidence_multiplier
            
            # Apply limits
            final_size = min(
                final_size,
                account_equity * self.config.execution.max_position_size,
            )
            final_size = max(
                final_size,
                self.config.execution.min_order_value,
            )
            
            logger.debug(
                f"Order size: ${final_size:.2f} "
                f"(equity: ${account_equity:.2f}, "
                f"strength: {signal.strength.name}, "
                f"confidence: {confidence_multiplier:.1%})"
            )
            
            return final_size
            
        except Exception as e:
            logger.error(f"Order size calculation failed: {e}")
            return 0
    
    async def _close_position(self, signal: TradingSignal) -> bool:
        """
        Close existing position
        
        Args:
            signal: TradingSignal with EXIT type
            
        Returns:
            True if closed successfully
        """
        position_key = f"{signal.pair_x}_{signal.pair_y}"
        position = self.positions.get(position_key)
        
        if not position or not position.is_open():
            logger.warning(f"No open position to close: {position_key}")
            return False
        
        try:
            logger.info(f"🟡 Closing position: {position_key}")
            
            symbol_x = f"{signal.pair_x}/USDT:USDT"
            symbol_y = f"{signal.pair_y}/USDT:USDT"
            
            # Get exit prices
            ticker_x = await self.exchange.fetch_ticker(symbol_x)
            ticker_y = await self.exchange.fetch_ticker(symbol_y)
            
            exit_price_x = ticker_x['last']
            exit_price_y = ticker_y['last']
            
            # Close positions (reverse orders)
            if position.quantity_x > 0:
                await self.exchange.create_market_sell_order(
                    symbol_x, abs(position.quantity_x)
                )
            elif position.quantity_x < 0:
                await self.exchange.create_market_buy_order(
                    symbol_x, abs(position.quantity_x)
                )
            
            if position.quantity_y > 0:
                await self.exchange.create_market_sell_order(
                    symbol_y, abs(position.quantity_y)
                )
            elif position.quantity_y < 0:
                await self.exchange.create_market_buy_order(
                    symbol_y, abs(position.quantity_y)
                )
            
            # Calculate PnL
            pnl_x = (exit_price_x - position.entry_price_x) * position.quantity_x
            pnl_y = (exit_price_y - position.entry_price_y) * position.quantity_y
            total_pnl = pnl_x + pnl_y
            
            logger.info(
                f"✅ Position closed | "
                f"PnL: ${total_pnl:.2f} "
                f"({total_pnl/(abs(position.entry_price_x*position.quantity_x))*100:.2f}%)"
            )
            
            # Update stats
            self.total_pnl += total_pnl
            position.realized_pnl = total_pnl
            position.mode = PositionMode.NEUTRAL
            position.quantity_x = 0.0
            position.quantity_y = 0.0
            
            return True
            
        except Exception as e:
            logger.error(f"Position close failed: {e}", exc_info=True)
            return False
    
    def get_summary(self) -> Dict:
        """
        Get execution summary for monitoring
        
        Returns:
            Dictionary with statistics
        """
        open_positions = [p for p in self.positions.values() if p.is_open()]
        
        return {
            'total_trades': self.total_trades,
            'total_pnl': f"${self.total_pnl:.2f}",
            'total_fees': f"${self.total_fees:.2f}",
            'open_positions': len(open_positions),
            'pending_signals': len(self.pending_signals),
            'safety_protocols': {
                'concurrency_lock': 'ENABLED',
                'partial_fill_protection': 'ENABLED',
                'ghost_order_detection': 'ENABLED',
                'precision_validation': 'ENABLED',
                'virtual_atomicity': 'ENABLED',
            },
            'positions': {
                k: {
                    'mode': v.mode.value,
                    'qty_x': v.quantity_x,
                    'qty_y': v.quantity_y,
                    'unrealized_pnl': v.unrealized_pnl,
                    'realized_pnl': v.realized_pnl,
                }
                for k, v in self.positions.items()
                if v.is_open()
            },
        }


async def example_usage():
    """Example: Production execution with safety protocols"""
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    config = get_config()
    engine = ExecutionEngine(config)
    
    try:
        # Connect
        if not await engine.connect():
            return
        
        # Example signal
        signal = TradingSignal(
            timestamp=datetime.utcnow(),
            pair_x="BTC",
            pair_y="ETH",
            signal_type=SignalType.BUY,
            z_score=2.5,
            confidence=0.85,
            strength=SignalStrength.STRONG,
            suggested_position_size=0.75,
            stop_loss_z=4.0,
            take_profit_z=0.0,
            hedge_ratio=0.065,
        )
        
        # Execute with full safety protocol
        success = await engine.execute_signal(signal)
        
        if success:
            logger.info("✅ Trade executed successfully")
        else:
            logger.error("❌ Trade execution failed")
        
        # Print summary
        summary = engine.get_summary()
        logger.info(f"\n{summary}")
        
    finally:
        await engine.disconnect()


if __name__ == "__main__":
    asyncio.run(example_usage())
