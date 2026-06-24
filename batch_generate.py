#!/usr/bin/env python3
"""批量生成 Keep 月视图示例截图，覆盖 2024-09 到 2026-06 共 22 个月

用法: python batch_generate.py [--scale 1|2|3]
"""

import argparse
import os
import random
import subprocess
import sys

random.seed(2024)

ap = argparse.ArgumentParser(description="批量生成 Keep 月视图截图")
ap.add_argument("--scale", type=int, default=1, choices=[1, 2, 3],
                help="缩放倍率: 1=@1x(390×844), 2=@2x(780×1688), 3=@3x(1170×2532) (默认 1)")
args = ap.parse_args()
SCALE = args.scale

# ── 学期规划 ─────────────────────────────────────────────────────
# 每学期 >= 80km / >= 40次（每次 >= 2km，由 generate_keep.py 保证）
# 按月相对均匀分配，月份间有轻微自然波动
# 最后一学期（2026春）仅 4 个月，同需达标

def alloc_semester(months, total_km, total_runs):
    """把学期目标分配到各月，返回 [(year,month, km, runs)]"""
    n = len(months)
    # 距离：保底每月 round(total_km/n * 0.6)，加大随机波动
    min_km = round(total_km / n * 0.6, 1)
    extra_km = total_km - min_km * n
    w_km = [random.uniform(0.4, 2.2) for _ in range(n)]
    s = sum(w_km)
    kms = [round(min_km + w / s * extra_km, 2) for w in w_km]
    diff = round(total_km - sum(kms), 2)
    kms[-1] = round(kms[-1] + diff, 2)

    # 次数：每月 5~9 次不等（6月学期）或 8~12 次（4月学期），总次数达标
    min_runs = 5 if n >= 6 else 8
    max_runs_per_month = 9 if n >= 6 else 12
    extra_runs = total_runs - min_runs * n
    w_runs = [random.uniform(0.5, 2.0) for _ in range(n)]
    ws_runs = sum(w_runs)
    runs_list = []
    for i in range(n):
        r = min_runs + int(w_runs[i] / ws_runs * extra_runs)
        r = min(r, max_runs_per_month)
        max_for_km = int(kms[i] / 2.0)
        runs_list.append(min(r, max_for_km))
    # 补足因取整/cap 丢失的次数
    while sum(runs_list) < total_runs:
        candidates = [i for i in range(n) if runs_list[i] < int(kms[i] / 2.0)]
        if not candidates:
            break
        i = random.choice(candidates)
        runs_list[i] += 1
    while sum(runs_list) > total_runs:
        i = random.randint(0, n - 1)
        if runs_list[i] > min_runs:
            runs_list[i] -= 1

    return [(months[i][0], months[i][1], kms[i], runs_list[i]) for i in range(n)]


# 四个学期：2024秋 → 2025春 → 2025秋 → 2026春
# 每次 >= 2km，所以 km 总量至少要能容纳 run 次数 (runs * 2.0)
semesters = [
    ("2024秋 (2024-09 ~ 2025-02)",
     [(2024,9),(2024,10),(2024,11),(2024,12),(2025,1),(2025,2)],
     90.0, 44),   # 44*2=88, 90km 足够
    ("2025春 (2025-03 ~ 2025-08)",
     [(2025,3),(2025,4),(2025,5),(2025,6),(2025,7),(2025,8)],
     90.0, 43),   # 43*2=86
    ("2025秋 (2025-09 ~ 2026-02)",
     [(2025,9),(2025,10),(2025,11),(2025,12),(2026,1),(2026,2)],
     92.0, 45),   # 45*2=90
    ("2026春 (2026-03 ~ 2026-06, 仅4月)",
     [(2026,3),(2026,4),(2026,5),(2026,6)],
     86.0, 42),   # 42*2=84
]

plan_entries = []
for name, months, km, runs in semesters:
    plan_entries.extend(alloc_semester(months, km, runs))

# 构建 {(year,month): (km, runs)} 格式，兼容后续代码
plan = {(y, m): (km, runs) for (y, m, km, runs) in plan_entries}

# ── 时间 & 总运动分钟累计 ────────────────────────────────────────
# 截图时间：模拟多次打开 App 的自然时间分布（跨越不同日/时段）
# 总运动分钟：历史累计，从一个合理初值开始每月累加当月跑步时长

cumulative_minutes = 3480

all_months = sorted(plan.keys())

# 生成自然的时间序列：每次推进 1~6 小时，控制在 06:00~23:00 之间
rng_time = random.Random(999)
time_list = []
cur_h = rng_time.randint(7, 9)
cur_m = rng_time.randint(0, 59)
for i in range(len(all_months)):
    time_list.append(f"{cur_h:02d}:{cur_m:02d}")
    cur_h += rng_time.randint(1, 6)
    cur_m += rng_time.randint(0, 30)
    if cur_m >= 60:
        cur_h += 1
        cur_m -= 60
    if cur_h >= 23:
        cur_h = rng_time.randint(6, 9)
        cur_m = rng_time.randint(0, 59)

print("=== 生成计划 ===")
for i, ym in enumerate(all_months):
    km, runs = plan[ym]
    run_min = int(km * 5.5)
    print(f"  {ym[0]}-{ym[1]:02d}  {km:.2f}km  {runs}次  ~{run_min}min  时间{time_list[i]}")

print()

out_dir = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(out_dir, exist_ok=True)

for i, ym in enumerate(all_months):
    year, month = ym
    km, runs = plan[ym]

    time_str = time_list[i]

    # 累计总运动分钟
    run_min = int(km * 5.5)
    other_min = random.randint(20, 45)
    cumulative_minutes += run_min + other_min

    out_file = os.path.join(out_dir, f"{year}-{month:02d}.png")
    seed = 2024 * 100 + i

    cmd = [
        sys.executable, "generate_keep.py",
        "--year", str(year),
        "--month", str(month),
        "--distance", str(km),
        "--runs", str(runs),
        "--time", time_str,
        "--total-minutes", str(cumulative_minutes),
        "--seed", str(seed),
        "--scale", str(SCALE),
        "--output", out_file,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ {year}-{month:02d}  {km:.2f}km  {runs}次  时间{time_str}  累计{cumulative_minutes}min")
    else:
        print(f"✗ {year}-{month:02d} 失败:", result.stderr.strip())

print("\n全部完成，文件在 output/ 目录")
