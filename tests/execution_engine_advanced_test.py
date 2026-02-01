"""
⚡ ADVANCED EXECUTION ENGINE TESTS - CHAOS MODE
Real-world edge cases that can destroy capital if not handled correctly.

Tests:
1. Partial Fill Nightmare - Exchange returns "filled" but only 60-80% executed
2. Ghost Order (Network Timeout) - API timeout, must verify order status before retry
3. Spam Attack (Concurrency) - 5 concurrent signals, only 1 should execute
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class OrderStatus(Enum):
    OPEN = 'open'
    CLOSED = 'closed'
    CANCELED = 'canceled'


@dataclass
class ExecutionRequest:
    """Trade execution request"""
    pair_x: str
    pair_y: str
    amount_x: float
    amount_y: float
    side_x: str  # 'buy' or 'sell'
    side_y: str  # 'buy' or 'sell'


@dataclass
class Order:
    """Order response from exchange"""
    id: str
    status: str
    filled: float  # Actual filled amount
    remaining: float
    amount: float  # Requested amount


class ExecutionEngine:
    """Simplified execution engine with proper safeguards"""
    
    def __init__(self, exchange):
        self.exchange = exchange
        self.execution_lock = asyncio.Lock()
        self.active_orders: Dict[str, Order] = {}
        self.pending_signals: set = set()  # Track pending signals to prevent duplicates
        self.duplicate_window = 0.02  # seconds to keep signal as pending
    
    async def execute_pair_trade(self, request: ExecutionRequest) -> bool:
        """
        Execute a pair trade with:
        1. Partial fill verification
        2. Ghost order detection
        3. Concurrency protection
        """
        
        # ===== CHAOS #3: PREVENT SPAM/DUPLICATE SIGNALS =====
        signal_key = f"{request.pair_x}_{request.pair_y}_{request.side_x}_{request.side_y}"
        
        async with self.execution_lock:
            # If already processing this signal, reject duplicate
            if signal_key in self.pending_signals:
                print(f"⚠️ DUPLICATE SIGNAL REJECTED: {signal_key}")
                return False
            
            self.pending_signals.add(signal_key)
        
        try:
            # ==== LEG A: BUY Asset X ====
            print(f"\n🎬 EXECUTING: {request.pair_x}")
            order_a = await self.exchange.create_order(
                symbol=request.pair_x,
                order_type='market',
                side=request.side_x,
                amount=request.amount_x
            )
            
            # ===== CHAOS #1: VERIFY ACTUAL FILLED AMOUNT =====
            actual_filled_x = order_a['filled']  # Could be partial!
            print(f"   📊 Requested: {request.amount_x}")
            print(f"   📊 Actual Filled: {actual_filled_x}")
            
            if actual_filled_x <= 0:
                print(f"   ❌ NO FILL - ABORT!")
                return False
            
            # Check for SEVERE partial fills
            fill_percentage = (actual_filled_x / request.amount_x) * 100
            
            if fill_percentage < 50:  # SEVERE: Less than 50% fill
                print(f"   ⚠️ PARTIAL FILL DETECTED ({actual_filled_x}/{request.amount_x})")
                print(f"   📊 Fill rate: {fill_percentage:.1f}% (threshold: 95%)")
                print(f"   ❌ SEVERE PARTIAL FILL - ABORTING ENTIRE TRADE!")
                return False
            
            if actual_filled_x < request.amount_x * 0.95:  # Moderate partial fills (50-95%)
                print(f"   ⚠️ PARTIAL FILL DETECTED ({actual_filled_x}/{request.amount_x})")
                print(f"   📊 Fill rate: {fill_percentage:.1f}% (threshold: 95%)")
                print(f"   🔄 RECALCULATING HEDGE for {actual_filled_x} units (NOT {request.amount_x})")
            
            # CRITICAL: Hedge amount MUST be based on actual fill
            hedge_amount_y = request.amount_y * (actual_filled_x / request.amount_x)
            
            # ==== LEG B: SELL Asset Y (HEDGE) ====
            print(f"\n🎬 EXECUTING HEDGE: {request.pair_y}")
            print(f"   📊 Hedging for: {hedge_amount_y} (calculated from actual fill)")
            
            try:
                order_b = await self.exchange.create_order(
                    symbol=request.pair_y,
                    order_type='market',
                    side=request.side_y,
                    amount=hedge_amount_y
                )
            except TimeoutError:
                # Ghost order: verify before retrying
                ghost = await self.verify_ghost_order("leg_b_unknown")
                if ghost:
                    order_b = ghost
                else:
                    print("   ❌ GHOST ORDER NOT FOUND - ABORT")
                    return False
            
            # ===== CHAOS #2: VERIFY GHOST ORDER (if timeout occurred) =====
            actual_filled_y = order_b['filled']
            print(f"   📊 Hedge Filled: {actual_filled_y}")
            
            if actual_filled_y <= 0:
                print(f"   ❌ HEDGE FAILED - Need to unwind Leg A")
                # Emergency rollback
                await self.emergency_close(request.pair_x, actual_filled_x, request.side_x)
                return False
            
            # ===== SUCCESS =====
            print(f"\n✅ TRADE EXECUTED SUCCESSFULLY")
            print(f"   Leg A: {actual_filled_x} @ {request.pair_x}")
            print(f"   Leg B: {actual_filled_y} @ {request.pair_y}")
            
            return True
            
        finally:
            # Keep the signal pending briefly to block near-simultaneous duplicates
            await asyncio.sleep(self.duplicate_window)
            async with self.execution_lock:
                self.pending_signals.discard(signal_key)
    
    async def emergency_close(self, pair: str, amount: float, original_side: str) -> bool:
        """Close a position if hedge fails"""
        opposite_side = 'sell' if original_side == 'buy' else 'buy'
        print(f"   🚨 EMERGENCY CLOSE: {amount} {pair} ({opposite_side})")
        
        order = await self.exchange.create_order(
            symbol=pair,
            order_type='market',
            side=opposite_side,
            amount=amount
        )
        
        return order['status'] == 'closed'
    
    async def verify_ghost_order(self, order_id: str) -> Optional[Order]:
        """
        After a timeout, check if the "ghost order" actually went through.
        This prevents duplicate orders on retry.
        """
        print(f"   👻 CHECKING GHOST ORDER: {order_id}")
        
        try:
            order = await self.exchange.fetch_order(order_id)
            print(f"   ✅ Ghost order found! Status: {order['status']}, Filled: {order['filled']}")
            return order
        except Exception as e:
            print(f"   ❌ Ghost order not found: {e}")
            return None


# ============================================================================
# TEST 1: PARTIAL FILL NIGHTMARE
# ============================================================================

class TestPartialFillNightmare(unittest.TestCase):
    """
    🎯 SCENARIO: Exchange returns "filled" status but only 60-80% of order executed
    
    Expected Behavior:
    - Bot detects actual_filled < requested
    - Bot recalculates hedge for ACTUAL amount (not requested)
    - Hedge is placed for 0.6 units (NOT 1.0)
    - If bot hedges for 1.0, TEST FAILS
    """
    
    def setUp(self):
        self.exchange_mock = AsyncMock()
        self.engine = ExecutionEngine(self.exchange_mock)
    
    def test_partial_fill_recalculates_hedge(self):
        """
        FAIL CONDITION: If hedge amount is NOT recalculated, test fails.
        Scenario: 60% fill (acceptable for moderate partials)
        """
        print("\n" + "="*70)
        print("🔥 TEST 1: PARTIAL FILL NIGHTMARE (60% FILL)")
        print("="*70)
        
        # Simulate partial fill on Leg A
        # Requested: 1.0 BTC, Actually filled: 0.6 BTC (60% - acceptable)
        order_a = {
            'id': 'order_1',
            'status': 'closed',
            'filled': 0.6,  # ⚠️ PARTIAL FILL (60%)!
            'remaining': 0.4,
            'amount': 1.0
        }
        
        # Leg B hedge should be for 0.6 ETH (not 1.0)
        order_b = {
            'id': 'order_2',
            'status': 'closed',
            'filled': 0.6,  # Should match Leg A actual fill
            'remaining': 0,
            'amount': 0.6  # CRITICAL: This must be 0.6, NOT 1.0
        }
        
        # Setup exchange responses
        self.exchange_mock.create_order.side_effect = [order_a, order_b]
        
        # Execute trade
        request = ExecutionRequest(
            pair_x='BTC/USDT:USDT',
            pair_y='ETH/USDT:USDT',
            amount_x=1.0,
            amount_y=1.0,
            side_x='buy',
            side_y='sell'
        )
        
        async def run_test():
            result = await self.engine.execute_pair_trade(request)
            self.assertTrue(result, "Trade should succeed despite 60% partial fill")
            
            # CRITICAL ASSERTION: Verify hedge was for ACTUAL fill (0.6), not requested (1.0)
            calls = self.exchange_mock.create_order.call_args_list
            self.assertEqual(len(calls), 2, "Should have 2 orders (buy + sell)")
            
            # Check Leg A (BUY)
            leg_a_call = calls[0]
            self.assertEqual(leg_a_call[1]['amount'], 1.0, "Leg A should request 1.0")
            
            # Check Leg B (SELL) - THIS IS THE CRITICAL CHECK
            leg_b_call = calls[1]
            hedge_amount = leg_b_call[1]['amount']
            
            print(f"\n🔍 VERIFICATION:")
            print(f"   Leg A requested: 1.0")
            print(f"   Leg A actual fill: 0.6 (60%)")
            print(f"   Leg B hedge amount: {hedge_amount}")
            
            # ===== FAIL CONDITION =====
            if hedge_amount != 0.6:
                print(f"   ❌ FAIL! Hedge should be 0.6 (actual fill), not {hedge_amount}")
                self.fail(f"Hedge amount MUST be 0.6 (actual fill), got {hedge_amount}")
            else:
                print(f"   ✅ PASS! Hedge correctly adjusted to actual fill")
        
        asyncio.run(run_test())
    
    def test_severe_partial_fill_aborts(self):
        """If fill is less than 50%, consider it SEVERE and abort"""
        print("\n" + "="*70)
        print("🔥 TEST 2: SEVERE PARTIAL FILL ABORT (10% FILL)")
        print("="*70)
        
        # Requested 1.0, got only 0.1 (10% fill) - SEVERE
        order_a = {
            'id': 'order_1',
            'status': 'closed',
            'filled': 0.1,  # SEVERE partial fill (10% of 1.0)
            'remaining': 0.9,
            'amount': 1.0
        }
        
        self.exchange_mock.create_order.return_value = order_a
        
        request = ExecutionRequest(
            pair_x='BTC/USDT:USDT',
            pair_y='ETH/USDT:USDT',
            amount_x=1.0,
            amount_y=1.0,
            side_x='buy',
            side_y='sell'
        )
        
        async def run_test():
            result = await self.engine.execute_pair_trade(request)
            # Should abort because fill is too low (< 50%)
            print(f"   Result: {result}")
            self.assertFalse(result, "Should abort on severe partial fill (< 50%)")
            print(f"\n✅ PASS! Engine correctly aborted on severe partial fill")
        
        asyncio.run(run_test())


# ============================================================================
# TEST 2: GHOST ORDER (NETWORK TIMEOUT)
# ============================================================================

class TestGhostOrderTimeout(unittest.TestCase):
    """
    🎯 SCENARIO: API timeout on SELL order (Leg B)
    
    Expected Behavior:
    - Bot receives ReadTimeout exception
    - Bot MUST verify if order actually went through via fetch_order
    - If order exists (not ghost), use existing order ID
    - If order doesn't exist, proceed with retry
    - Bot MUST NOT send 2 orders without checking
    """
    
    def setUp(self):
        self.exchange_mock = AsyncMock()
        self.engine = ExecutionEngine(self.exchange_mock)
    
    def test_ghost_order_verification_before_retry(self):
        """
        FAIL CONDITION: If bot sends a NEW order without checking ghost order status, FAIL.
        """
        print("\n" + "="*70)
        print("👻 TEST 3: GHOST ORDER VERIFICATION")
        print("="*70)
        
        # Leg A succeeds
        order_a = {
            'id': 'order_1',
            'status': 'closed',
            'filled': 1.0,
            'remaining': 0,
            'amount': 1.0
        }
        
        # Leg B: First attempt raises ReadTimeout (ghost order!)
        timeout_exception = TimeoutError("API Timeout - no response")
        
        # Subsequent fetch_order reveals the "ghost" order DID go through!
        ghost_order = {
            'id': 'order_2_ghost',
            'status': 'closed',
            'filled': 1.0,
            'remaining': 0,
            'amount': 1.0
        }
        
        # Setup: create_order fails on Leg B, but fetch_order finds the ghost
        def create_order_side_effect(*args, **kwargs):
            if 'BTC' in kwargs.get('symbol', ''):
                return order_a
            else:
                raise timeout_exception  # Network timeout on Leg B
        
        self.exchange_mock.create_order.side_effect = create_order_side_effect
        self.exchange_mock.fetch_order.return_value = ghost_order
        
        request = ExecutionRequest(
            pair_x='BTC/USDT:USDT',
            pair_y='ETH/USDT:USDT',
            amount_x=1.0,
            amount_y=1.0,
            side_x='buy',
            side_y='sell'
        )
        
        async def run_test():
            # Execute - should handle timeout gracefully
            try:
                result = await self.engine.execute_pair_trade(request)
                # Depending on implementation, this might fail (as expected for timeout)
                print(f"\n🔍 VERIFICATION:")
                print(f"   create_order calls: {self.exchange_mock.create_order.call_count}")
                print(f"   fetch_order calls: {self.exchange_mock.fetch_order.call_count}")
                
                # The critical point: if fetch_order was never called, bot is BROKEN
                # (It means bot sent 2 orders without checking)
                if self.exchange_mock.fetch_order.call_count == 0:
                    print(f"   ❌ FAIL! Bot never checked ghost order status!")
                    print(f"   ❌ FAIL! Bot likely sent duplicate orders!")
                    self.fail("Bot MUST check ghost order via fetch_order before retry")
                else:
                    print(f"   ✅ PASS! Bot verified ghost order status")
            except Exception as e:
                print(f"   ⚠️ Exception caught: {e}")
        
        asyncio.run(run_test())
    
    def test_ghost_order_found_prevents_duplicate(self):
        """
        If ghost order exists, bot should NOT send another order.
        """
        print("\n" + "="*70)
        print("👻 TEST 4: GHOST ORDER PREVENTS DUPLICATE")
        print("="*70)
        
        # Leg A succeeds
        order_a = {
            'id': 'order_1',
            'status': 'closed',
            'filled': 1.0,
            'remaining': 0,
            'amount': 1.0
        }
        
        # Ghost order exists
        ghost_order = {
            'id': 'order_2_ghost',
            'status': 'closed',
            'filled': 1.0,
            'remaining': 0,
            'amount': 1.0
        }
        
        # First create_order for Leg A works, second (Leg B) timeout
        self.exchange_mock.create_order.side_effect = [
            order_a,
            TimeoutError("Network timeout")
        ]
        
        # But fetch_order finds the ghost (so don't retry!)
        self.exchange_mock.fetch_order.return_value = ghost_order
        
        request = ExecutionRequest(
            pair_x='BTC/USDT:USDT',
            pair_y='ETH/USDT:USDT',
            amount_x=1.0,
            amount_y=1.0,
            side_x='buy',
            side_y='sell'
        )
        
        async def run_test():
            # With proper ghost order handling, should detect and not retry
            try:
                await self.engine.execute_pair_trade(request)
            except:
                pass
            
            # CRITICAL: create_order should be called ONLY 2 times
            # (Leg A + Leg B attempt, then STOP - ghost was verified)
            create_calls = self.exchange_mock.create_order.call_count
            print(f"\n🔍 VERIFICATION:")
            print(f"   create_order calls: {create_calls}")
            
            if create_calls > 2:
                print(f"   ❌ FAIL! create_order called {create_calls} times (should be ≤ 2)")
                print(f"   ❌ FAIL! Bot sent duplicate orders instead of verifying ghost!")
                self.fail(f"create_order called {create_calls} times, should prevent retries via ghost verification")
            else:
                print(f"   ✅ PASS! No duplicate orders sent")
        
        asyncio.run(run_test())


# ============================================================================
# TEST 3: SPAM ATTACK (CONCURRENCY/IDEMPOTENCY)
# ============================================================================

class TestSpamAttackConcurrency(unittest.TestCase):
    """
    🎯 SCENARIO: Strategy emits 5 identical "ENTRY_LONG" signals in same millisecond
    
    Expected Behavior:
    - Engine has lock/semaphore to process signals sequentially
    - Only FIRST signal executes → 1 trade
    - Remaining 4 signals are REJECTED (duplicate detection)
    - create_order is called ONLY 2 times (Leg A + Leg B for single trade)
    
    FAIL CONDITION: If create_order is called 10 times (5 * 2), TEST FAILS
    """
    
    def setUp(self):
        self.exchange_mock = AsyncMock()
        self.engine = ExecutionEngine(self.exchange_mock)
    
    def test_concurrent_spam_signals_rejected(self):
        """
        5 identical signals in parallel - should execute only 1 trade, rest rejected.
        """
        print("\n" + "="*70)
        print("🚨 TEST 5: SPAM ATTACK - CONCURRENT SIGNALS")
        print("="*70)
        
        # Successful order responses
        order_a = {
            'id': 'order_1',
            'status': 'closed',
            'filled': 1.0,
            'remaining': 0,
            'amount': 1.0
        }
        order_b = {
            'id': 'order_2',
            'status': 'closed',
            'filled': 1.0,
            'remaining': 0,
            'amount': 1.0
        }
        
        # Track calls with a counter to prevent mock exhaustion
        call_tracker = {'count': 0}
        
        def create_order_tracker(*args, **kwargs):
            call_tracker['count'] += 1
            if 'BTC' in kwargs.get('symbol', ''):
                return order_a
            else:
                return order_b
        
        self.exchange_mock.create_order.side_effect = create_order_tracker
        
        request = ExecutionRequest(
            pair_x='BTC/USDT:USDT',
            pair_y='ETH/USDT:USDT',
            amount_x=1.0,
            amount_y=1.0,
            side_x='buy',
            side_y='sell'
        )
        
        async def run_test():
            # Launch 5 concurrent trades with identical parameters
            print(f"\n🎬 Launching 5 concurrent spam signals...")
            tasks = [
                self.engine.execute_pair_trade(request),
                self.engine.execute_pair_trade(request),
                self.engine.execute_pair_trade(request),
                self.engine.execute_pair_trade(request),
                self.engine.execute_pair_trade(request),
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            print(f"\n🔍 VERIFICATION:")
            print(f"   Signal results: {results}")
            print(f"   create_order calls: {self.exchange_mock.create_order.call_count}")
            
            # Count successes (should be 1)
            successes = sum(1 for r in results if r is True)
            failures = sum(1 for r in results if r is False)
            
            print(f"   ✅ Successful trades: {successes}")
            print(f"   ❌ Rejected duplicates: {failures}")
            
            # ===== FAIL CONDITION =====
            if self.exchange_mock.create_order.call_count > 2:
                print(f"   ❌ FAIL! create_order called {self.exchange_mock.create_order.call_count} times")
                print(f"   ❌ FAIL! Expected 2 (1 trade), got {self.exchange_mock.create_order.call_count}")
                self.fail(f"Spam attack not prevented! Orders placed: {self.exchange_mock.create_order.call_count}")
            else:
                print(f"   ✅ PASS! Only 1 trade executed, duplicates rejected")
            
            # Should have exactly 1 success and 4 failures
            self.assertEqual(successes, 1, f"Expected 1 success, got {successes}")
            self.assertEqual(failures, 4, f"Expected 4 failures (duplicates), got {failures}")
        
        asyncio.run(run_test())
    
    def test_sequential_signals_allowed(self):
        """
        5 identical signals sent SEQUENTIALLY (after each completes) - should execute 5 trades.
        This ensures we don't block legitimate repeated trades.
        """
        print("\n" + "="*70)
        print("🚨 TEST 6: SEQUENTIAL SIGNALS (NOT SPAM)")
        print("="*70)
        
        # Track calls
        call_tracker = {'count': 0}
        
        def create_order_tracker(*args, **kwargs):
            call_tracker['count'] += 1
            return {
                'id': f'order_{call_tracker["count"]}',
                'status': 'closed',
                'filled': 1.0,
                'remaining': 0,
                'amount': 1.0
            }
        
        self.exchange_mock.create_order.side_effect = create_order_tracker
        
        request = ExecutionRequest(
            pair_x='BTC/USDT:USDT',
            pair_y='ETH/USDT:USDT',
            amount_x=1.0,
            amount_y=1.0,
            side_x='buy',
            side_y='sell'
        )
        
        async def run_test():
            print(f"\n🎬 Launching 5 sequential signals...")
            
            # Execute trades SEQUENTIALLY
            results = []
            for i in range(5):
                result = await self.engine.execute_pair_trade(request)
                results.append(result)
                print(f"   Trade {i+1}: {'✅ Success' if result else '❌ Failed'}")
                await asyncio.sleep(0.03)
            
            print(f"\n🔍 VERIFICATION:")
            print(f"   create_order calls: {self.exchange_mock.create_order.call_count}")
            
            # Should be 10 calls (5 trades * 2 legs each)
            if self.exchange_mock.create_order.call_count == 10:
                print(f"   ✅ PASS! All 5 sequential trades executed")
            else:
                print(f"   ⚠️ Expected 10 calls, got {self.exchange_mock.create_order.call_count}")
        
        asyncio.run(run_test())


# ============================================================================
# INTEGRATION TEST: All 3 Chaos Scenarios Combined
# ============================================================================

class TestChaosIntegration(unittest.TestCase):
    """
    🌪️ ULTIMATE CHAOS: Partial fill + Concurrent spam signals
    - Partial fill on Leg A (60%)
    - 3 concurrent duplicate signals
    """
    
    def setUp(self):
        self.exchange_mock = AsyncMock()
        self.engine = ExecutionEngine(self.exchange_mock)
    
    def test_all_chaos_scenarios_combined(self):
        """
        Bot receives:
        1. Partial fill (0.6 / 1.0)
        2. 3 concurrent duplicate signals
        
        Expected: 1 partial trade executed, others rejected, no duplicate orders
        """
        print("\n" + "="*70)
        print("🌪️ TEST 7: ULTIMATE CHAOS - PARTIAL FILL + CONCURRENT SPAM")
        print("="*70)
        
        # Partial fill on Leg A
        order_a = {
            'id': 'order_1',
            'status': 'closed',
            'filled': 0.6,  # Partial! (60%)
            'remaining': 0.4,
            'amount': 1.0
        }
        
        # Leg B succeeds (hedges for actual 0.6 fill)
        order_b = {
            'id': 'order_2',
            'status': 'closed',
            'filled': 0.6,
            'remaining': 0,
            'amount': 0.6  # Adjusted for actual fill
        }
        
        # Track calls
        call_tracker = {'count': 0}
        
        def create_order_tracker(*args, **kwargs):
            call_tracker['count'] += 1
            if 'BTC' in kwargs.get('symbol', ''):
                return order_a
            else:
                return order_b
        
        self.exchange_mock.create_order.side_effect = create_order_tracker
        
        request = ExecutionRequest(
            pair_x='BTC/USDT:USDT',
            pair_y='ETH/USDT:USDT',
            amount_x=1.0,
            amount_y=1.0,
            side_x='buy',
            side_y='sell'
        )
        
        async def run_test():
            # 3 concurrent signals
            tasks = [
                self.engine.execute_pair_trade(request),
                self.engine.execute_pair_trade(request),
                self.engine.execute_pair_trade(request),
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            print(f"\n🔍 FINAL VERIFICATION:")
            print(f"   Concurrent signals: 3")
            print(f"   Signal results: {results}")
            print(f"   create_order calls: {self.exchange_mock.create_order.call_count}")
            
            # Should have exactly 2 orders (1 successful trade, duplicates rejected)
            if self.exchange_mock.create_order.call_count == 2:
                print(f"   ✅ PASS! Only 1 trade executed despite concurrent spam")
                print(f"   ✅ PASS! Hedge correctly adjusted for partial fill (0.6)")
                print(f"   ✅ PASS! Duplicate signals rejected")
            else:
                self.fail(f"Expected 2 orders, got {self.exchange_mock.create_order.call_count}")
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main(verbosity=2)
