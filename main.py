"""DeepDip strategy for the make.fun 24-hour BTC race."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
from makefun_bars import BPS, run

SYMBOL = "CBBTC"
WARMUP = 30
DIP_BPS = 220
STAB_WIN = 20
STAB_BPS = 20
TP_BPS = 220
STOP_BPS = 120
MAX_HOLD = 600
STALL_AFTER = 300
STALL_WIN = 60
STALL_BPS = 30
MAX_ENTRIES = 2
FALLBACK_SEQ = 1000
MOM_WIN = 30
MOM_BPS = 60
COOLDOWN = 120
SIZE_BPS = 9800
MAX_SLIPPAGE_BPS = 500


class Strategy:
    def __init__(self):
        self.closes = []
        self.entry_price = None
        self.entry_seq = None
        self.entries = 0
        self.cooldown_until = 0

    def on_batch(self, state, batch):
        for fill in batch["fills"]:
            if fill["symbol"] != SYMBOL or fill["status"] != "filled":
                continue
            if fill["side"] == "buy":
                self.entry_price = int(fill["price"])
                self.entry_seq = state.seq
                self.entries += 1
            elif fill["side"] == "sell":
                self.entry_price = None
                self.entry_seq = None
                self.cooldown_until = state.seq + COOLDOWN

        bar = next((bar for bar in batch["bars"] if bar["symbol"] == SYMBOL), None)
        if bar is None:
            return []

        price = int(bar["c"])
        self.closes.append(price)
        last_close_ms = state.hello["first_close_ms"] + (state.warmup_bars + 1439) * 60_000
        if state.warming_up or state.t >= last_close_ms or len(self.closes) < WARMUP:
            return []

        scaled_price = price * BPS
        position = state.positions.get(SYMBOL)
        if position is not None and position.qty > 0:
            if self.entry_price is None:
                return []

            held = state.seq - self.entry_seq
            stopped = scaled_price <= self.entry_price * (BPS - STOP_BPS)
            target_reached = scaled_price // self.entry_price >= BPS + TP_BPS
            stalled = (
                held >= STALL_AFTER
                and len(self.closes) > STALL_WIN
                and scaled_price < self.closes[-1 - STALL_WIN] * (BPS - STALL_BPS)
            )
            if stopped or target_reached or stalled or held >= MAX_HOLD:
                return [{
                    "side": "sell",
                    "symbol": SYMBOL,
                    "qty": position.qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
            return []

        if self.entries >= MAX_ENTRIES or state.seq < self.cooldown_until:
            return []

        stabilized_dip = (
            scaled_price < self.closes[0] * (BPS - DIP_BPS)
            and scaled_price >= self.closes[-1 - STAB_WIN] * (BPS - STAB_BPS)
            and price > self.closes[-2]
        )
        late_momentum = (
            len(self.closes) >= FALLBACK_SEQ
            and scaled_price > self.closes[-1 - MOM_WIN] * (BPS + MOM_BPS)
        )
        if stabilized_dip or late_momentum:
            notional = min(state.cash * SIZE_BPS // BPS, state.weight_room(SYMBOL))
            minimum = int(state.hello["fees"]["min_notional_quote_units"])
            if notional >= minimum:
                return [{
                    "side": "buy",
                    "symbol": SYMBOL,
                    "notional_quote_units": notional,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
        return []


if __name__ == "__main__":
    run(Strategy().on_batch)
