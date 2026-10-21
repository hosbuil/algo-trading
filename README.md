# Algorithmic trading research pipeline

Go ingests Binance spot closed 1-minute candles → CSV → Python/PyTorch trains an LSTM → held-out signal CSV → C++ simulates long/cash exposure.

## Run
From this project directory, with Go 1.22+, Python 3.10+, and a C++17 compiler:

```sh
mkdir -p build data
cd ingest
go mod download
go build -o ../build/ingest .
cd ..
./build/ingest -symbol btcusdt -out data/bars.csv
# Stop with Ctrl-C after collecting data; or supply historical minute bars.
python3 -m venv .venv
.venv/bin/pip install -r ml/requirements.txt
.venv/bin/python ml/train.py --epochs 10
clang++ -O3 -std=c++17 backtest/main.cpp -o build/backtest
./build/backtest data/signals.csv 10
```
For an offline plumbing demo, run `python3 ml/demo.py` instead of ingestion. It writes 10,000 synthetic bars; synthetic results do not measure predictive value.

## Contracts and timing
`bars.csv`: `timestamp,close`, UTC Unix milliseconds, strictly contiguous 60,000-ms steps, positive prices. Each timestamp denotes candle start; close becomes available one minute later. Use one symbol per file. The collector creates a new file exclusively, reconnects with bounded exponential backoff, handles interrupt shutdown, suppresses duplicate candles, and logs gaps. It does not recover missed history; repair gaps from a historical source before training. CSV writes use buffering and backpressure rather than an unbounded queue. Closed candles reduce training I/O; this is not a tick-level capture engine.

`signals.csv`: `timestamp,close,signal`, where 1 means fully long and 0 means cash. The LSTM receives 32 standardized log returns and predicts the next return's sign. Scaling and training use only the first 70% of the history. The final 30% supplies held-out predictions. The fixed probability threshold is 0.55; no holdout tuning is performed. `data/model.pt` contains weights, scaling, and window metadata.

A signal observed at close t executes at close t+1. Existing exposure earns the intervening return; the new position starts earning returns afterward. Costs in basis points apply at every entry/exit and final liquidation (default 10 bps combined fees/slippage). Final pending signals are not executed. Output reports equity starting at 1, total return, maximum drawdown, fill count, and elapsed parsing/simulation time.

## Scope and next steps
This is a runnable research scaffold, not a production execution service. It has no broker orders, exchange credentials, leverage, shorting, funding, spread/order-book fills, market impact, portfolio allocation, historical downloader, or live model inference. It makes no profitability claim. Use walk-forward evaluation and independent data before interpreting results. Report a buy-and-hold benchmark, uncertainty, and turnover alongside any predictive score.

The backtester is a single-pass O(n) streaming engine with O(1) simulation memory. CSV parsing uses standard streams; benchmark representative history before asserting years in seconds. Production tick throughput would require measured load tests, durable queues, gap recovery, and a compact columnar or binary format. Training currently materializes windows in memory and needs a lazy dataset for very large histories.

## Verification
C++17 compilation and checks for delayed execution, two-sided costs, and gap rejection passed. Python files passed syntax compilation. Full PyTorch training requires installing the dependencies. Live exchange connectivity and sustained throughput have not been validated.

API references: [Binance spot WebSocket specification](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md), [PyTorch LSTM](https://docs.pytorch.org/docs/stable/generated/torch.nn.modules.rnn.LSTM.html).
