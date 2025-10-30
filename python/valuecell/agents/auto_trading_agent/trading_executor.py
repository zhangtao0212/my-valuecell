"""Trading execution and position management (refactored)"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import (
    AutoTradingConfig,
    PortfolioValueSnapshot,
    Position,
    PositionHistorySnapshot,
    TechnicalIndicators,
    TradeAction,
    TradeHistoryRecord,
    TradeType,
)
from .position_manager import PositionManager
from .trade_recorder import TradeRecorder

logger = logging.getLogger(__name__)


class TradingExecutor:
    """
    Orchestrates trade execution using specialized modules.

    This is the main facade that coordinates:
    - Position management (via PositionManager)
    - Trade recording (via TradeRecorder)
    - Cash management (via PositionManager)
    """

    def __init__(self, config: AutoTradingConfig):
        """
        Initialize trading executor.

        Args:
            config: Auto trading configuration
        """
        self.config = config
        self.initial_capital = config.initial_capital

        # Use specialized modules
        self._position_manager = PositionManager(config.initial_capital)
        self._trade_recorder = TradeRecorder()

    def execute_trade(
        self,
        symbol: str,
        action: TradeAction,
        trade_type: TradeType,
        indicators: TechnicalIndicators,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a trade (open or close position).

        Args:
            symbol: Trading symbol
            action: Trade action (buy/sell)
            trade_type: Trade type (long/short)
            indicators: Current technical indicators

        Returns:
            Trade execution details or None if execution failed
        """
        try:
            current_price = indicators.close_price
            timestamp = datetime.now(timezone.utc)

            if action == TradeAction.BUY:
                return self._execute_buy(symbol, trade_type, current_price, timestamp)
            elif action == TradeAction.SELL:
                return self._execute_sell(symbol, trade_type, current_price, timestamp)

            return None

        except Exception as e:
            logger.error(f"Failed to execute trade for {symbol}: {e}")
            return None

    def _execute_buy(
        self,
        symbol: str,
        trade_type: TradeType,
        current_price: float,
        timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Open a new position"""
        # Check if we already have a position
        if self._position_manager.get_position(symbol) is not None:
            logger.info(f"Position already exists for {symbol}, skipping")
            return None

        # Check max positions limit
        if self._position_manager.get_positions_count() >= self.config.max_positions:
            logger.info(f"Max positions reached ({self.config.max_positions})")
            return None

        # Calculate position size
        available_cash = self._position_manager.get_available_cash()
        risk_amount = available_cash * self.config.risk_per_trade
        quantity = risk_amount / current_price
        notional = quantity * current_price

        # Check if we have enough cash
        if notional > available_cash:
            logger.warning(
                f"Insufficient cash: need ${notional:.2f}, have ${available_cash:.2f}"
            )
            return None

        # Create and open position
        position = Position(
            symbol=symbol,
            entry_price=current_price,
            quantity=quantity if trade_type == TradeType.LONG else -quantity,
            entry_time=timestamp,
            trade_type=trade_type,
            notional=notional,
        )

        if not self._position_manager.open_position(symbol, position):
            return None

        # Record trade
        portfolio_value = self.get_portfolio_value()
        trade_record = TradeHistoryRecord(
            timestamp=timestamp,
            symbol=symbol,
            action="opened",
            trade_type=trade_type.value,
            price=current_price,
            quantity=abs(position.quantity),
            notional=notional,
            pnl=None,
            portfolio_value_after=portfolio_value,
            cash_after=self._position_manager.get_available_cash(),
        )
        self._trade_recorder.record_trade(trade_record)

        return {
            "action": "opened",
            "trade_type": trade_type.value,
            "symbol": symbol,
            "entry_price": current_price,
            "quantity": position.quantity,
            "notional": notional,
            "timestamp": timestamp,
        }

    def _execute_sell(
        self,
        symbol: str,
        trade_type: TradeType,
        current_price: float,
        timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Close an existing position"""
        # Get position
        position = self._position_manager.get_position(symbol)
        if position is None:
            return None

        # Check if trade type matches
        if position.trade_type != trade_type:
            return None

        # Calculate P&L
        pnl = self._position_manager.calculate_position_pnl(position, current_price)
        exit_notional = abs(position.quantity) * current_price

        # Close position
        self._position_manager.close_position(symbol)
        self._position_manager.release_cash(position.notional, pnl)

        # Record trade
        holding_time = timestamp - position.entry_time
        portfolio_value = self.get_portfolio_value()
        trade_record = TradeHistoryRecord(
            timestamp=timestamp,
            symbol=symbol,
            action="closed",
            trade_type=trade_type.value,
            price=current_price,
            quantity=abs(position.quantity),
            notional=exit_notional,
            pnl=pnl,
            portfolio_value_after=portfolio_value,
            cash_after=self._position_manager.get_available_cash(),
        )
        self._trade_recorder.record_trade(trade_record)

        return {
            "action": "closed",
            "trade_type": trade_type.value,
            "symbol": symbol,
            "entry_price": position.entry_price,
            "exit_price": current_price,
            "quantity": position.quantity,
            "entry_notional": position.notional,
            "exit_notional": exit_notional,
            "pnl": pnl,
            "holding_time": holding_time,
            "timestamp": timestamp,
        }

    # ============ Portfolio Queries ============

    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        total_value, _, _ = self._position_manager.calculate_portfolio_value()
        return total_value

    def get_portfolio_summary(self) -> Dict:
        """Get complete portfolio summary"""
        return self._position_manager.get_portfolio_summary()

    def get_current_capital(self) -> float:
        """Get available cash"""
        return self._position_manager.get_available_cash()

    @property
    def current_capital(self) -> float:
        """Property for backward compatibility"""
        return self._position_manager.get_available_cash()

    @property
    def positions(self) -> Dict[str, Position]:
        """Property for backward compatibility"""
        return self._position_manager.get_all_positions()

    # ============ History Management ============

    def snapshot_positions(self, timestamp: datetime):
        """Take a snapshot of all positions"""
        self._position_manager.snapshot_positions(timestamp)

    def snapshot_portfolio(self, timestamp: datetime):
        """Take a snapshot of portfolio value"""
        self._position_manager.snapshot_portfolio(timestamp)

    def get_trade_history(self) -> List[TradeHistoryRecord]:
        """Get all trade history"""
        return self._trade_recorder.get_all_trades()

    def get_position_history(self) -> List[PositionHistorySnapshot]:
        """Get all position snapshots"""
        return self._position_manager.get_position_history()

    def get_portfolio_history(self) -> List[PortfolioValueSnapshot]:
        """Get all portfolio snapshots"""
        return self._position_manager.get_portfolio_history()

    # ============ Statistics ============

    def get_trade_statistics(self) -> Dict:
        """Get trading statistics"""
        return self._trade_recorder.get_trade_statistics()

    def get_symbol_statistics(self, symbol: str) -> Dict:
        """Get statistics for a symbol"""
        return self._trade_recorder.get_symbol_statistics(symbol)

    def get_daily_statistics(self) -> Dict[str, Dict]:
        """Get daily P&L breakdown"""
        return self._trade_recorder.get_daily_statistics()

    # ============ Management ============

    def reset(self, initial_capital: float):
        """Reset executor state"""
        self._position_manager.reset(initial_capital)
        self._trade_recorder.reset()
