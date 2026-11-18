# DeepDip

DeepDip trades cbBTC against USDC on one-minute bars. It waits for a deep dip
below the day's opening reference (the first close it receives), then buys
once or twice if prices stabilize. It holds for a recovery with a take-profit,
a hard stop, a stall exit, and a maximum holding time. A late momentum fallback
gives it a chance to trade on days without a qualifying dip.

Run with `python3 main.py`. It uses only the Python standard library.
The `vendor/` directory holds the make.fun kit SDK, which reads the hello
handshake and bar batches on stdin and writes one order reply per batch on stdout.
