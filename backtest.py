import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import itertools
import json

ORDER_SIZE = 5000
STEP = 25  # more granular now

def get_snapshots(df):
    snapshots = []
    for ts, group in df.groupby("ts_event"):
        venues = []
        for _, row in group.iterrows():
            venue = {
                'id': row['publisher_id'],
                'ask': row['ask_px_00'],
                'ask_size': row['ask_sz_00'],
                'fee': 0.002 + 0.001 * (hash(row['publisher_id']) % 3),
                'rebate': 0.001 + 0.001 * (hash(row['publisher_id']) % 2)
            }
            venues.append(venue)
        snapshots.append(venues)
    return snapshots

def compute_cost(split, venues, order_size, λo, λu, θ):
    executed = 0
    cash_spent = 0
    for i, alloc in enumerate(split):
        exe = min(alloc, venues[i]['ask_size'])
        executed += exe
        cash_spent += exe * (venues[i]['ask'] + venues[i]['fee'])
        rebate = max(alloc - exe, 0) * venues[i]['rebate']
        cash_spent -= rebate

    underfill = max(order_size - executed, 0)
    overfill = max(executed - order_size, 0)
    penalty = λu * underfill + λo * overfill + θ * (underfill + overfill)
    return cash_spent + penalty

def allocate(order_size, venues, λo, λu, θ, step=STEP):
    N = len(venues)
    best_cost = float('inf')
    best_split = None
    for split in itertools.product(range(0, order_size + 1, step), repeat=N):
        total_alloc = sum(split)
        if total_alloc == 0 or total_alloc > order_size:
            continue
        cost = compute_cost(split, venues, order_size, λo, λu, θ)
        if cost < best_cost:
            best_cost = cost
            best_split = split
    return (best_split, best_cost) if best_split else (None, None)

def run_backtest(snapshots, λo, λu, θ):
    total_cash = 0
    filled = 0
    fill_record = []

    for i, venues in enumerate(snapshots):
        if filled >= ORDER_SIZE:
            break
        to_fill = ORDER_SIZE - filled
        split, _ = allocate(to_fill, venues, λo, λu, θ)
        if split is None:
            print(f"Snapshot {i}: No valid allocation.")
            continue

        print(f"\nSnapshot {i}: Allocation = {split}")
        for j, alloc in enumerate(split):
            venue = venues[j]
            fill = min(alloc, venue['ask_size'])
            if fill > 0:
                cost = fill * (venue['ask'] + venue['fee'])
                print(f"  Venue {venue['id']}: Alloc={alloc}, AskSize={venue['ask_size']}, Filled={fill}")
                total_cash += cost
                filled += fill
                fill_record.append((filled, total_cash))
            if filled >= ORDER_SIZE:
                break

    avg_price = total_cash / filled if filled else 0
    print(f"\nTotal filled: {filled} / {ORDER_SIZE} | Avg price: {avg_price:.4f}")
    return total_cash, avg_price, fill_record

def baseline_best_ask(snapshots):
    cash, filled = 0, 0
    for venues in snapshots:
        if filled >= ORDER_SIZE:
            break
        best = min(venues, key=lambda v: v['ask'])
        to_fill = min(best['ask_size'], ORDER_SIZE - filled)
        cash += to_fill * (best['ask'] + best['fee'])
        filled += to_fill
    return cash, cash / filled if filled else 0

def parameter_sweep(snapshots):
    param_grid = list(itertools.product([0.01, 0.03, 0.05],
                                        [0.02, 0.04, 0.06],
                                        [0.0001, 0.001, 0.005]))
    best_params = None
    best_result = float('inf')
    best_output = None

    for λo, λu, θ in param_grid:
        print(f"\nTrying λo={λo}, λu={λu}, θ={θ}")
        total_cash, avg_price, record = run_backtest(snapshots, λo, λu, θ)
        if total_cash < best_result and total_cash > 0:
            best_result = total_cash
            best_params = {"lambda_over": λo, "lambda_under": λu, "theta_queue": θ}
            best_output = (total_cash, avg_price, record)

    return best_params, best_output

def plot_cumulative(record):
    if not record or len(record) < 2:
        print("Not enough data to plot.")
        return
    filled, cost = zip(*record)
    plt.plot(filled, cost)
    plt.xlabel("Cumulative Shares Filled")
    plt.ylabel("Cumulative Cost")
    plt.title("Smart Order Router Execution")
    plt.grid(True)
    plt.savefig("results.png")
    print("Saved plot as results.png")

def main():
    df = pd.read_csv("l1_day.csv")
    df = df.sort_values("ts_event")
    df = df.drop_duplicates(subset=["ts_event", "publisher_id"], keep="first")
    snapshots = get_snapshots(df)

    best_params, best_output = parameter_sweep(snapshots)
    if not best_output:
        print("❌ No valid allocation found across all parameters.")
        return

    best_total_cash, best_avg_price, best_record = best_output
    baseline_cash, baseline_avg = baseline_best_ask(snapshots)

    results = {
        "best_params": best_params,
        "best_total_cash": round(best_total_cash, 3),
        "best_avg_price": round(best_avg_price, 3),
        "baseline_best_ask": round(baseline_cash, 3),
        "baseline_best_ask_avg": round(baseline_avg, 6),
        "savings_vs_best_ask_bps": 10000 * (baseline_avg - best_avg_price) / baseline_avg
    }

    print(json.dumps(results, indent=2))
    plot_cumulative(best_record)

if __name__ == "__main__":
    main()
