# Smart Order Router (Cont & Kukanov Model)

## What This Is

This is a Python project for backtesting a Smart Order Router based on the cost model introduced by Rama Cont & Arseniy Kukanov (2014). 

The goal is to intelligently split a 5,000-share buy order across multiple venues to minimize cost and execution risk, rather than executing the full order on a single exchange.

## Cost Model

The router uses a convex cost model that penalizes:
- Overfilling (buying more than needed)
- Underfilling (not buying enough)
- Queue risk (the chance that limit orders don’t get filled)

These are controlled by three parameters:
- `lambda_over`: cost of overfilling
- `lambda_under`: cost of underfilling
- `theta_queue`: cost of queue execution risk

## How It Works

- Parses a stream of market data (`l1_day.csv`)
- At each market snapshot:
  - Builds a per-venue quote snapshot
  - Uses a brute-force allocator to try every valid share split (in 25-share increments)
  - Allows partial allocations, penalizes shortfalls
- Tests a grid of parameter values for the three penalties
- Benchmarks the optimal strategy against a basic best-ask execution strategy
- Outputs a JSON summary of results
- Generates a cumulative cost plot (`results.png`) if enough data is available

## Requirements

- Python 3.8+
- `pandas`
- `numpy`
- `matplotlib`

Install dependencies with:

```bash
pip install pandas numpy matplotlib
