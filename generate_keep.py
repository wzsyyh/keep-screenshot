#!/usr/bin/env python3
"""
Keep 月视图示例截图生成器
用法: python3 generate_keep.py --year 2025 --month 9 --distance 22.5 --runs 12
"""

import argparse
import calendar
import os
import platform
import random
import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

SYSTEM = platform.system()

if SYSTEM == "Darwin":
    FONT_REGULAR_PATHS = [
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
        "86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ]
    FONT_BOLD_PATHS = [
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
        "86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ]
    SF_FONT_PATHS = [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ]
elif SYSTEM == "Linux":
    # 微软雅黑 Light（iOS 风格偏细）+ Bold + 常规回退
    FONT_REGULAR_PATHS = [
        "/mnt/c/Windows/Fonts/msyhl.ttc",        # Microsoft YaHei Light
        "/mnt/c/Windows/Fonts/msyh.ttc",
        "/mnt/c/Windows/Fonts/simhei.ttf",
    ]
    FONT_BOLD_PATHS = [
        "/mnt/c/Windows/Fonts/msyhbd.ttc",       # Microsoft YaHei Bold
        "/mnt/c/Windows/Fonts/msyh.ttc",
        "/mnt/c/Windows/Fonts/simhei.ttf",
    ]
    SF_FONT_PATHS = [
        "/mnt/c/Windows/Fonts/segoeuib.ttf",     # Segoe UI Bold (≈ SF Pro Text Bold)
        "/mnt/c/Windows/Fonts/segoeuisl.ttf",    # Segoe UI Semilight
        "/mnt/c/Windows/Fonts/segoeui.ttf",
        "/mnt/c/Windows/Fonts/msyh.ttc",
    ]
else:
    FONT_REGULAR_PATHS = []
    FONT_BOLD_PATHS = []
    SF_FONT_PATHS = []

# 从真实 Keep 截图里提取的状态栏右侧图标（信号+wifi+电池），放在脚本同目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUSBAR_ICONS_PATH = os.path.join(SCRIPT_DIR, "statusbar_icons_1x.png")
# 完整状态栏底板（右侧图标已保留，左侧时间区域已清空），用于直接贴图
STATUSBAR_BASE_PATH = os.path.join(SCRIPT_DIR, "statusbar_base.png")
# 原始 Keep 截图，用于提取状态栏图标（如 statusbar_icons_1x.png 不存在时自动生成）
STATUSBAR_SOURCE_PATH = (
    "/var/folders/ql/d9y1zl053pj53kbqrllgfn6h0000gn/T/aionui/f3989016/"
    "a4d0f0490a8c6957afbf15dec3435838.png"
) if SYSTEM == "Darwin" else STATUSBAR_BASE_PATH

# 配色
WHITE       = (255, 255, 255)
BLACK       = (20,  20,  20)
LIGHT_GRAY  = (248, 248, 248)
MID_GRAY    = (200, 200, 200)
GRAY        = (150, 150, 150)
DARK_GRAY   = (60,  60,  60)
GREEN       = (82,  196, 26)
GREEN_DARK  = (56,  158, 13)
GREEN_FILL  = (82,  196, 26, 45)
BORDER      = (235, 235, 235)


def font(size, bold=False):
    """加载字体，优先平台中文字体（regular/bold 分路径），回退到默认字体"""
    paths = FONT_BOLD_PATHS if bold else FONT_REGULAR_PATHS
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def sf_font(size):
    """加载状态栏时间字体（macOS 用 San Francisco，其他平台优先 Bold）"""
    for path in SF_FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return font(size, bold=True)


def gen_runs(year, month, target_distance, target_runs):
    """随机生成跑步记录，使距离和次数接近目标"""
    days_in_month = calendar.monthrange(year, month)[1]
    run_count = min(target_runs, days_in_month)

    run_days = sorted(random.sample(range(1, days_in_month + 1), run_count))

    # 分配距离：每次保底 MIN_RUN km，次数受限于总距离
    MIN_RUN = 2.0
    max_runs_by_dist = int(target_distance / MIN_RUN) if MIN_RUN > 0 else target_runs
    run_count = min(target_runs, days_in_month, max(1, max_runs_by_dist))
    run_days = sorted(random.sample(range(1, days_in_month + 1), run_count))
    extra = max(0.0, target_distance - run_count * MIN_RUN)
    weights = [random.random() for _ in range(run_count)]
    w_sum = sum(weights)
    distances = [round(MIN_RUN + w / w_sum * extra, 2) for w in weights]
    # 修正四舍五入误差（diff 此时必为非负，不会跌破 MIN_RUN）
    diff = round(target_distance - sum(distances), 2)
    distances[-1] = round(distances[-1] + diff, 2)

    runs = []
    for day, dist in zip(run_days, distances):
        # 配速稳定在 4'50" ~ 5'10"
        pace_min = 4
        pace_sec = random.randint(50, 70)
        if pace_sec >= 60:
            pace_min = 5
            pace_sec -= 60
        pace_total = pace_min * 60 + pace_sec
        total_sec = int(dist * pace_total)
        h = total_sec // 3600
        m = (total_sec % 3600) // 60
        s = total_sec % 60
        duration = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        runs.append({
            "day": day,
            "distance": dist,
            "pace_min": pace_min,
            "pace_sec": pace_sec,
            "pace": f"{pace_min}'{pace_sec:02d}\"",
            "duration": duration,
            "calories": int(dist * 58 + random.randint(-20, 20)),
        })
    return runs


def draw_rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width)


def generate(year, month, target_distance, target_runs, time_str=None, output=None, total_minutes=None, scale=1):
    SCALE = scale
    BASE_W, BASE_H = 393, 852   # iPhone 15 Pro logical resolution
    W, H = BASE_W * SCALE, BASE_H * SCALE

    def s(v):
        return int(round(v * SCALE))

    DPI_MAP = {1: 163, 2: 326, 3: 458}
    dpi_val = DPI_MAP.get(SCALE, 72)

    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    runs = gen_runs(year, month, target_distance, target_runs)
    total_dist = round(sum(r["distance"] for r in runs), 2)
    total_cals = sum(r["calories"] for r in runs)
    total_count = len(runs)

    all_pace_sec = [r["pace_min"] * 60 + r["pace_sec"] for r in runs]
    avg_pace_sec = sum(all_pace_sec) // len(all_pace_sec)
    ap_m, ap_s = avg_pace_sec // 60, avg_pace_sec % 60
    avg_pace = f"{ap_m}'{ap_s:02d}\""

    total_sec = sum(int(r["distance"] * (r["pace_min"] * 60 + r["pace_sec"])) for r in runs)
    th = total_sec // 3600
    tm = (total_sec % 3600) // 60
    ts = total_sec % 60
    total_dur = f"{th:02d}:{tm:02d}:{ts:02d}"

    # 总运动（分钟）= Keep 历史累计，必须远大于本月跑步时长
    # 默认推算：假设用户从大约1~2年前开始使用，平均每月运动约180~300分钟
    this_month_min = total_sec // 60
    if total_minutes is None:
        months_active = random.randint(14, 24)
        avg_monthly = random.randint(170, 290)
        total_minutes = months_active * avg_monthly + this_month_min + random.randint(0, 50)

    if time_str is None:
        now = datetime.now()
        time_str = f"{now.hour:02d}:{now.minute:02d}"

    y = 0

    # ── 状态栏 ──────────────────────────────────────────────────
    # 贴真实底板（含右侧图标），再在左侧写时间，风格完全一致
    if os.path.exists(STATUSBAR_BASE_PATH):
        bar_img = Image.open(STATUSBAR_BASE_PATH).convert("RGBA")
        bw, bh = bar_img.size
        if bw != W or SCALE > 1:
            bar_h = int(bh * W / bw)
            bar_img = bar_img.resize((W, bar_h), Image.LANCZOS)
        else:
            bar_h = bh
        # 白色底 + 状态栏 alpha 合成
        bar_bg = Image.new("RGB", (W, bar_h), WHITE)
        bar_bg.paste(bar_img, (0, 0), bar_img)
        img.paste(bar_bg, (0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((s(22), int(bar_h * 0.58)), time_str, fill=BLACK, font=sf_font(s(16)), anchor="lm")
    elif os.path.exists(STATUSBAR_ICONS_PATH):
        bar_h = s(46)
        draw.rectangle([0, 0, W, bar_h], fill=WHITE)
        draw.text((s(22), int(bar_h * 0.58)), time_str, fill=BLACK, font=font(s(15), bold=True), anchor="lm")
        icons_img = Image.open(STATUSBAR_ICONS_PATH).convert("RGBA")
        iw, ih = icons_img.size
        if SCALE > 1:
            icons_img = icons_img.resize((iw * SCALE, ih * SCALE), Image.LANCZOS)
            iw, ih = icons_img.size
        img.paste(icons_img, (W - iw, (bar_h - ih) // 2), icons_img)
        draw = ImageDraw.Draw(img)
    else:
        bar_h = s(46)
        draw.rectangle([0, 0, W, bar_h], fill=WHITE)
        draw.text((s(22), bar_h // 2), time_str, fill=BLACK, font=font(s(15), bold=True), anchor="lm")

    y = bar_h

    # ── 标题栏 ──────────────────────────────────────────────────
    draw.rectangle([0, y, W, y + s(48)], fill=WHITE)
    # 返回箭头
    draw.text((s(18), y + s(24)), "<", fill=BLACK, font=font(s(26)), anchor="lm")
    # 标题
    draw.text((W // 2, y + s(24)), "运动记录", fill=BLACK, font=font(s(17), bold=True), anchor="mm")
    # 右侧图标（分享 + 更多）
    draw.text((W - s(44), y + s(24)), "↑", fill=DARK_GRAY, font=font(s(15)), anchor="mm")
    draw.text((W - s(18), y + s(24)), "…", fill=DARK_GRAY, font=font(s(15)), anchor="mm")

    y += s(48)

    # ── 顶部统计 Tab（滚动区域） ──────────────────────────────
    draw.rectangle([0, y, W, y + s(52)], fill=WHITE)
    draw.line([0, y + s(51), W, y + s(51)], fill=BORDER, width=s(1))

    top_tabs = [
        ("总运动(分钟)", str(total_minutes)),
        (f"总跑步(公里)", f"{total_dist:.2f}"),
        (f"户外跑步(公里)", f"{total_dist:.2f}"),
    ]
    tw = W // 3
    for i, (lbl, val) in enumerate(top_tabs):
        tx = i * tw
        cx = tx + tw // 2
        # 选中第2个tab（总跑步）
        if i == 1:
            draw.rectangle([tx + s(4), y + s(4), tx + tw - s(4), y + s(48)], outline=BLACK, width=s(1))
        draw.text((cx, y + s(16)), lbl if len(lbl) <= 8 else lbl[:6] + "…", fill=DARK_GRAY if i == 1 else GRAY,
                  font=font(s(10)), anchor="mt")
        draw.text((cx, y + s(30)), val, fill=BLACK if i == 1 else GRAY,
                  font=font(s(13), bold=True), anchor="mt")

    y += s(52)

    # ── 时间维度 Tab（日/周/月/年/总）──────────────────────────
    draw.rectangle([0, y, W, y + s(44)], fill=WHITE)
    tabs = ["日", "周", "月", "年", "总"]
    tw2 = W // len(tabs)
    for i, t in enumerate(tabs):
        tx = i * tw2
        cx = tx + tw2 // 2
        if t == "月":
            draw_rounded_rect(draw, [tx + s(5), y + s(7), tx + tw2 - s(5), y + s(37)], radius=s(8), fill=(240, 240, 240))
        draw.text((cx, y + s(22)), t, fill=BLACK if t == "月" else GRAY,
                  font=font(s(14), bold=(t == "月")), anchor="mm")

    y += s(44)
    draw.line([0, y, W, y], fill=BORDER, width=s(1))
    y += s(1)

    # ── 月份导航 ─────────────────────────────────────────────
    draw.rectangle([0, y, W, y + s(46)], fill=WHITE)
    draw.text((s(22), y + s(23)), "<", fill=GRAY, font=font(s(20)), anchor="lm")
    draw.text((W // 2, y + s(23)), f"{year}年{month}月 ▼", fill=BLACK, font=font(s(15), bold=True), anchor="mm")
    draw.text((W - s(22), y + s(23)), ">", fill=GRAY, font=font(s(20)), anchor="rm")

    y += s(46)

    # ── 距离标题 ─────────────────────────────────────────────
    draw.text((s(22), y + s(16)), "里程(公里)", fill=GRAY, font=font(s(12)), anchor="lm")
    y += s(32)

    # ── 大数字 ───────────────────────────────────────────────
    draw.text((s(22), y + s(8)), f"{total_dist:.2f}", fill=BLACK, font=font(s(50), bold=True), anchor="lt")
    y += s(66)

    # ── 统计行 ───────────────────────────────────────────────
    draw.rectangle([0, y, W, y + s(52)], fill=WHITE)
    stats = [
        ("消耗(千卡)", str(total_cals)),
        ("平均配速", avg_pace),
        ("时长", total_dur),
        ("完成(次)", str(total_count)),
    ]
    sw = W // 4
    for i, (lbl, val) in enumerate(stats):
        cx = i * sw + sw // 2
        draw.text((cx, y + s(12)), lbl, fill=GRAY, font=font(s(10)), anchor="mt")
        draw.text((cx, y + s(28)), val, fill=DARK_GRAY, font=font(s(13), bold=True), anchor="mt")

    y += s(52)

    # ── 折线图 ───────────────────────────────────────────────
    ch_top = y + s(50)
    ch_bottom = y + s(185)
    ch_left = s(24)
    ch_right = W - s(24)
    ch_w = ch_right - ch_left
    ch_h = ch_bottom - ch_top

    days_in_month = calendar.monthrange(year, month)[1]
    day_dist = {r["day"]: r["distance"] for r in runs}

    # 累计数组：每天一个数据点，非跑步日距离不变
    cum = []
    acc = 0.0
    for d in range(1, days_in_month + 1):
        acc += day_dist.get(d, 0)
        cum.append(acc)
    max_c = max(cum) if cum else 1

    # 折线数据点（每日一个，非跑步日持平）
    pts = []
    run_day_set = set(day_dist.keys())
    for i in range(days_in_month):
        px = ch_left + int(i * ch_w / max(1, days_in_month - 1))
        py = ch_bottom - int(cum[i] / max_c * ch_h)
        pts.append((px, py))

    # 密集插值仅用于填充抗锯齿
    dense_pts = []
    for i in range(len(pts)):
        if i == 0:
            dense_pts.append(pts[i])
        else:
            x0, y0 = pts[i - 1]
            x1, y1 = pts[i]
            steps = max(3, (x1 - x0))
            for j in range(steps):
                t = j / steps
                dense_pts.append((int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t)))

    # ── 超采样渲染（4x）— 网格线 → 填充 → 折线，逐层叠加 ──
    SS = 4
    CH_MARGIN = s(24)  # 四周留白防止折线端点和填充边缘被裁剪
    oss_w = (ch_w + 2 * CH_MARGIN) * SS
    oss_h = (ch_h + 2 * CH_MARGIN) * SS
    chart_ov = Image.new("RGBA", (oss_w, oss_h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(chart_ov)

    def ox(x):
        return int((x - ch_left + CH_MARGIN) * SS)

    def oy(y):
        return int((y - ch_top + CH_MARGIN) * SS)

    def ov(v):
        return int(v * SS)

    # 1) 网格线（底层，仅图表区域内）
    for gi in range(5):
        gy_rel = int(gi * ch_h / 4)
        gy_oss = oy(ch_top + gy_rel)
        cd.line([(ox(ch_left), gy_oss), (ox(ch_right), gy_oss)],
                fill=(238, 238, 238, 255), width=ov(1))

    # 2) 半透明绿色填充（中层，网格线透出）
    fill_os = [(ox(px), oy(py)) for (px, py) in dense_pts]
    fill_os += [(ox(ch_right), oy(ch_bottom)), (ox(ch_left), oy(ch_bottom))]
    cd.polygon(fill_os, fill=GREEN_FILL)

    # 3) 折线：直线连接每日数据点；跑步日交点画圆使过渡圆滑
    line_os = [(ox(px), oy(py)) for (px, py) in pts]
    for i in range(len(line_os) - 1):
        cd.line([line_os[i], line_os[i + 1]], fill=GREEN + (255,), width=ov(7))

    # 拐角处微小圆点柔化，不突兀
    joint_r = ov(2)
    for i in range(len(pts)):
        if i == 0 or i == len(pts) - 1 or cum[i] != cum[i - 1] or cum[i] != cum[i + 1]:
            px, py = pts[i]
            cd.ellipse([ox(px) - joint_r, oy(py) - joint_r,
                        ox(px) + joint_r, oy(py) + joint_r], fill=GREEN + (255,))

    # 终点大实心圆
    ex, ey = pts[-1]
    dot_r_os = ov(14)
    cd.ellipse([ox(ex) - dot_r_os, oy(ey) - dot_r_os,
                ox(ex) + dot_r_os, oy(ey) + dot_r_os], fill=GREEN + (255,))

    # 缩回目标尺寸，不裁剪——用偏移粘贴，保留留白区域避免边缘裁切
    chart_ov = chart_ov.resize((oss_w // SS, oss_h // SS), Image.LANCZOS)

    # 合入主图（偏移粘贴，CH_MARGIN 部分超出图表区但透明）
    img_rgba = img.convert("RGBA")
    img_rgba.paste(chart_ov, (ch_left - CH_MARGIN, ch_top - CH_MARGIN), chart_ov)
    img = img_rgba.convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── 原生分辨率：气泡（文字保证清晰）──────────────────
    # 终点实心圆已在超采样层，此处只画气泡
    tip_text = f"{total_dist:.2f}公里"
    tip_w, tip_h = s(90), s(28)
    tip_x = min(max(ex - tip_w // 2, ch_left), ch_right - tip_w)
    tip_y = ey - tip_h - s(12)
    draw_rounded_rect(draw, [tip_x, tip_y, tip_x + tip_w, tip_y + tip_h],
                      radius=s(6), fill=GREEN)
    draw.polygon([(ex - s(5), tip_y + tip_h),
                  (ex + s(5), tip_y + tip_h),
                  (ex, tip_y + tip_h + s(8))], fill=GREEN)
    draw.text((tip_x + tip_w // 2, tip_y + tip_h // 2),
              tip_text, fill=WHITE, font=font(s(10), bold=True), anchor="mm")

    # X 轴标签（原生分辨率）
    label_days = [1, 5, 10, 15, 20, 25]
    for ld in label_days:
        if ld <= days_in_month:
            lx = ch_left + int((ld - 1) * ch_w / (days_in_month - 1))
            draw.text((lx, ch_bottom + s(9)), f"{ld}日", fill=GRAY, font=font(s(9)), anchor="mt")
    draw.text((ch_right, ch_bottom + s(9)), f"{days_in_month}日", fill=GRAY, font=font(s(9)), anchor="mt")

    y = ch_bottom + s(32)
    draw.line([0, y, W, y], fill=BORDER, width=s(1))
    y += s(1)

    # ── 跑步记录列表 ─────────────────────────────────────────
    row_h = s(76)
    for run in reversed(runs):
        row_bottom = y + row_h
        partial = row_bottom > H

        draw.rectangle([0, y, W, min(row_bottom, H)], fill=WHITE)

        # 左侧小图标
        icon_left = s(14)
        icon_top = y + s(10)
        icon_right = s(36)
        icon_bottom = y + s(32)
        draw.ellipse([icon_left, icon_top, icon_right, icon_bottom], fill=(240, 250, 235))
        draw.ellipse([icon_left, icon_top, icon_right, icon_bottom], outline=GREEN, width=s(2))

        col_x = s(40)
        draw.text((col_x, y + s(21)), "户外跑步", fill=DARK_GRAY, font=font(s(14), bold=True), anchor="lm")
        draw.text((col_x, y + s(38)), f"{run['distance']:.2f} 公里", fill=DARK_GRAY, font=font(s(13)))
        draw.text((col_x, y + s(58)), f"用时 {run['duration']}  配速 {run['pace']}",
                  fill=GRAY, font=font(s(10)))

        date_str = f"{year}年{month}月{run['day']}日"
        draw.text((W - s(16), y + s(16)), date_str, fill=GRAY, font=font(s(11)), anchor="rt")

        line_y = min(row_bottom - s(1), H - s(1))
        if line_y > y:
            draw.line([s(16), line_y, W - s(16), line_y], fill=BORDER, width=s(1))

        y += row_h
        if y >= H:
            break

    if output is None:
        suffix = f"@{SCALE}x" if SCALE > 1 else ""
        output = f"keep_monthly_{year}_{month:02d}{suffix}.png"

    img.save(output, dpi=(dpi_val, dpi_val))
    print(f"✓ 已生成: {output} ({W}x{H}, {dpi_val} DPI)")
    print(f"  {year}年{month}月 | 距离 {total_dist:.2f}km | {total_count}次 | 消耗 {total_cals}千卡")
    return output


def main():
    ap = argparse.ArgumentParser(description="生成 Keep 月视图示例截图")
    ap.add_argument("--year",          type=int,   default=2025, help="年份 (默认 2025)")
    ap.add_argument("--month",         type=int,   default=9,    help="月份 (默认 9)")
    ap.add_argument("--distance",      type=float, default=22.0, help="当月跑步总距离 km (默认 22.0)")
    ap.add_argument("--runs",          type=int,   default=12,   help="当月跑步次数 (默认 12)")
    ap.add_argument("--time",          type=str,   default=None, help="截图时间显示，如 09:30")
    ap.add_argument("--output",        type=str,   default=None, help="输出文件路径")
    ap.add_argument("--seed",          type=int,   default=None, help="随机种子，固定可复现")
    ap.add_argument("--total-minutes", type=int,   default=None, help="Keep 历史总运动分钟数（默认自动推算一个合理大值）")
    ap.add_argument("--scale",         type=int,   default=1,    choices=[1, 2, 3], help="缩放倍率: 1=@1x(390×844), 2=@2x(780×1688), 3=@3x(1170×2532) (默认 1)")
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    generate(
        year=args.year,
        month=args.month,
        target_distance=args.distance,
        target_runs=args.runs,
        time_str=args.time,
        output=args.output,
        total_minutes=args.total_minutes,
        scale=args.scale,
    )


if __name__ == "__main__":
    main()
