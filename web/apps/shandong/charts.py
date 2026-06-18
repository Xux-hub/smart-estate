"""
动态图表生成模块
复用 analysis/shandong_analysis.py 中的绘图逻辑，返回 BytesIO 供 Django 视图使用
"""
import os, re, warnings
warnings.filterwarnings('ignore')

import numpy as np, pandas as pd
from io import BytesIO
from collections import Counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.ticker as ticker
import seaborn as sns
from matplotlib.colors import to_rgba

from django.db.models import Count, Avg
from web.apps.house.models import City, House

# ── 中文字体初始化（只执行一次）──
_FONT_INITED = False
def _init_font():
    global _FONT_INITED
    if _FONT_INITED:
        return
    for f in os.listdir(matplotlib.get_cachedir()):
        if 'font' in f.lower():
            try:
                os.remove(os.path.join(matplotlib.get_cachedir(), f))
            except OSError:
                pass
    fp = fm.FontProperties(fname='C:/Windows/Fonts/simhei.ttf')
    fn = fp.get_name()
    plt.rcParams['font.family'] = fn
    plt.rcParams['axes.unicode_minus'] = False
    sns.set_style("whitegrid")
    plt.rcParams['font.family'] = fn
    _FONT_INITED = True


def _fig_to_response(fig, dpi=120):
    """将 matplotlib figure 转为 Django HttpResponse 可用的 BytesIO"""
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════
#  全省维度图表（一级页面使用）
# ═══════════════════════════════════════════════

def chart_desc_stats():
    """① 描述性统计表（各城市对比）"""
    _init_font()
    stats = City.objects.all().values('name', 'house_count', 'avg_unit_price')
    # 转成类似 pandas 的结构方便复用绘图逻辑
    rows, names = [], []
    for c in stats:
        names.append(c['name'])
        rows.append([c['house_count'], float(c['avg_unit_price'] or 0)])
    if not rows:
        return None

    cities = names
    data_arr = np.array(rows)

    fig, ax = plt.subplots(figsize=(10, 0.5 * len(cities) + 1.5))
    ax.axis('off')

    col_widths = [1.2, 2.5, 3.5]
    row_h = 0.5
    x0, y0 = 0, 0
    headers = ['城市', '房源数量（套）', '平均单价（元/㎡）']

    def _rect(x, y, w, h):
        return plt.Rectangle((x, y), w, h, linewidth=0.8, edgecolor='white')

    for j, h in enumerate(headers):
        cx = sum(col_widths[:j])
        r = _rect(cx, y0, col_widths[j], row_h)
        r.set_facecolor('#2C3E50')
        ax.add_patch(r)
        ax.text(cx + col_widths[j] / 2, y0 + row_h / 2, h,
                ha='center', va='center', fontsize=11, fontweight='bold', color='white')

    for i in range(len(cities)):
        y = y0 + row_h * (i + 1)
        bg = '#ECF0F1' if i % 2 == 0 else 'white'

        r0 = _rect(x0, y, col_widths[0], row_h)
        r0.set_facecolor(bg)
        ax.add_patch(r0)
        ax.text(x0 + col_widths[0] / 2, y + row_h / 2, cities[i],
                ha='center', va='center', fontsize=10, fontweight='bold')

        for j in range(2):
            cx = sum(col_widths[:j + 1])
            vals = data_arr[:, j]
            vmin, vmax = vals.min(), vals.max()
            norm = (data_arr[i, j] - vmin) / (vmax - vmin) if vmax > vmin else 0.5
            cmap = plt.cm.Blues if j == 0 else plt.cm.Reds
            rgba = list(to_rgba(cmap(norm)))
            rgba[3] = 0.25 + 0.65 * norm
            r = _rect(cx, y, col_widths[j + 1], row_h)
            r.set_facecolor(rgba)
            ax.add_patch(r)
            val_str = f'{int(data_arr[i, j]):,}' if j == 0 else f'{data_arr[i, j]:,.2f}'
            ax.text(cx + col_widths[j + 1] / 2, y + row_h / 2, val_str,
                    ha='center', va='center', fontsize=10,
                    color='black' if norm < 0.6 else 'white')

    total_w = sum(col_widths)
    total_h = row_h * (len(cities) + 1)
    ax.set_xlim(0, total_w)
    ax.set_ylim(total_h + 0.3, 0)
    ax.set_title('山东省各城市房价描述性统计', fontsize=14, fontweight='bold', pad=12)
    plt.tight_layout()
    return _fig_to_response(fig, dpi=150)


def chart_housing_count():
    """② 房源数量柱状图"""
    _init_font()
    data = City.objects.all().values('name', 'house_count')
    names = [c['name'] + '市' for c in data]
    counts = [c['house_count'] for c in data]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(names, counts, color=sns.color_palette('Blues_r', len(names)), edgecolor='white')
    for b, v in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 30, f'{v:,}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_title('山东省各城市房源数量统计', fontsize=14, fontweight='bold')
    ax.set_ylabel('房源数量（套）', fontsize=11)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
    plt.xticks(rotation=30, fontsize=10)
    plt.tight_layout()
    return _fig_to_response(fig)


def chart_avg_price():
    """③ 平均房价柱状图"""
    _init_font()
    data = City.objects.all().values('name', 'avg_unit_price')
    names = [c['name'] + '市' for c in data]
    prices = [float(c['avg_unit_price'] or 0) for c in data]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(names, prices, color=sns.color_palette('Reds_r', len(names)), edgecolor='white')
    for b, v in zip(bars, prices):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 30, f'{v:,.0f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_title('山东省各城市平均房价统计', fontsize=14, fontweight='bold')
    ax.set_ylabel('平均单价（元/㎡）', fontsize=11)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    plt.xticks(rotation=30, fontsize=10)
    plt.tight_layout()
    return _fig_to_response(fig)


def chart_listing_trend():
    """④ 月度挂牌趋势折线图"""
    _init_font()
    # 用 ORM 按月份聚合，避免加载全部数据
    qs = House.objects.all().values('shijian')
    dates = []
    for row in qs:
        t = str(row['shijian'] or '')
        m = re.match(r'(\d{4}/\d{1,2})', t)
        if m:
            dates.append(m.group(1))
    if not dates:
        return None
    counter = Counter(dates)
    sorted_months = sorted(counter.keys())
    values = [counter[m] for m in sorted_months]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(range(len(sorted_months)), values, marker='o', linewidth=2, markersize=5, color='#2E86AB')
    ax.fill_between(range(len(sorted_months)), values, alpha=0.12, color='#2E86AB')
    for i, (xi, yi) in enumerate(zip(sorted_months, values)):
        if i % 3 == 0:
            ax.annotate(str(yi), (i, yi), textcoords="offset points",
                        xytext=(0, 10), ha='center', fontsize=8)
    ax.set_xticks(range(len(sorted_months)))
    ax.set_xticklabels(sorted_months, rotation=45, fontsize=9)
    ax.set_title('山东省二手房挂牌数量月度变化', fontsize=14, fontweight='bold')
    ax.set_ylabel('挂牌数量（套）', fontsize=11)
    plt.tight_layout()
    return _fig_to_response(fig)


def chart_high_end():
    """⑩ 高端小区热词图（单价 > 6万元/㎡）"""
    _init_font()
    qs = House.objects.filter(unit_price__gt=60000) \
        .values('mingcheng', 'unit_price')[:50]
    if not qs:
        return None
    df = pd.DataFrame(list(qs))
    stats = df.groupby('mingcheng').agg(
        count=('unit_price', 'count'),
        avg_price=('unit_price', 'mean')
    ).sort_values('count', ascending=False).head(20)

    fig, ax = plt.subplots(figsize=(10, 6))
    norm = plt.Normalize(stats['avg_price'].min(), stats['avg_price'].max())
    colors = plt.cm.YlOrRd(norm(stats['avg_price'].values))
    bars = ax.barh(stats.index[::-1], stats['count'].values[::-1],
                    color=colors[::-1], edgecolor='white', height=0.6)
    for b, (_, row) in zip(bars, stats.iloc[::-1].iterrows()):
        ax.text(b.get_width() + 0.2, b.get_y() + b.get_height() / 2,
                f'{row["count"]}套 | 均价{row["avg_price"]:,.0f}元/㎡',
                va='center', fontsize=8)
    sm = plt.cm.ScalarMappable(cmap='YlOrRd', norm=norm)
    sm.set_array([])
    plt.colorbar(sm, ax=ax, shrink=0.6).set_label('平均单价（元/㎡）', fontsize=10)
    ax.set_title('高端小区分布（单价 > 6万元/㎡）', fontsize=14, fontweight='bold')
    ax.set_xlabel('房源数量（套）', fontsize=10)
    plt.tight_layout()
    return _fig_to_response(fig)


def chart_wordcloud():
    """⑪ 小区词云图"""
    _init_font()
    try:
        from wordcloud import WordCloud
    except ModuleNotFoundError:
        chart_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            'analysis',
            'shandong_charts',
            '11_community_wordcloud.png',
        )
        with open(chart_path, 'rb') as f:
            return BytesIO(f.read())
    from PIL import Image, ImageDraw

    qs = House.objects.all().values('mingcheng')
    freq = {}
    for row in qs:
        name = str(row['mingcheng'] or '').strip()
        if name:
            freq[name] = freq.get(name, 0) + 1
    if not freq:
        return None

    size = (400, 400)
    mask_img = Image.new('L', size, 255)
    draw = ImageDraw.Draw(mask_img)
    draw.polygon([(200, 40), (340, 170), (60, 170)], fill=0)
    draw.rectangle([60, 170, 340, 370], fill=0)
    draw.rectangle([170, 280, 230, 370], fill=255)
    draw.rectangle([90, 210, 140, 270], fill=255)
    draw.rectangle([260, 210, 310, 270], fill=255)
    mask = np.array(mask_img)

    wc = WordCloud(
        font_path='C:/Windows/Fonts/simhei.ttf',
        mask=mask, background_color='white',
        max_font_size=60, min_font_size=8,
        max_words=150, width=400, height=400,
        colormap='Set2', random_state=42,
    ).generate_from_frequencies(freq)

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    ax.set_title('山东省热门小区词云图', fontsize=14, fontweight='bold')
    plt.tight_layout()
    return _fig_to_response(fig, dpi=150)


# ═══════════════════════════════════════════════
#  城市维度图表（二级页面使用）
# ═══════════════════════════════════════════════

def _load_city_df(city_name):
    """加载某城市的房源数据到 DataFrame"""
    qs = House.objects.filter(city=city_name).values(
        'huxing', 'louceng', 'mianji', 'zhuangxiu', 'unit_price', 'price', 'mingcheng', 'shijian')
    df = pd.DataFrame(list(qs))
    if df.empty:
        return df
    df['mianji_num'] = df['mianji'].apply(
        lambda v: float(re.search(r'\d+(?:\.\d+)?', str(v)).group(0))
        if v and re.search(r'\d+(?:\.\d+)?', str(v)) else None)
    df['floor_level'] = df['louceng'].apply(
        lambda t: '低楼层' if t and str(t).strip().startswith('低') else
                  '中楼层' if t and str(t).strip().startswith('中') else
                  '高楼层' if t and str(t).strip().startswith('高') else '其他')
    intervals = [(0, 60, '<60㎡'), (60, 90, '60-90㎡'), (90, 120, '90-120㎡'),
                 (120, 150, '120-150㎡'), (150, 200, '150-200㎡'), (200, 999, '>200㎡')]
    df['area_group'] = df['mianji_num'].apply(
        lambda m: next((l for lo, hi, l in intervals if lo <= (m or 0) < hi), '>200㎡')
        if not pd.isna(m) else '未知')
    return df


def chart_top5_layouts(city_name):
    """⑤ 各城市热门户型 Top5"""
    _init_font()
    data = House.objects.filter(city=city_name) \
        .values('huxing').annotate(cnt=Count('id')).order_by('-cnt')[:5]
    if not data:
        return None
    names = [d['huxing'] or '未知' for d in data][::-1]
    counts = [d['cnt'] for d in data][::-1]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(names, counts, color=sns.color_palette('Set2', 5), height=0.5)
    for i, v in enumerate(counts):
        ax.text(v + 0.5, i, str(v), va='center', fontsize=11, fontweight='bold')
    ax.set_title(f'{city_name}热门户型 Top5', fontsize=14, fontweight='bold')
    ax.set_xlabel('数量（套）', fontsize=11)
    plt.tight_layout()
    return _fig_to_response(fig)


def chart_floor_pie(city_name):
    """⑥ 楼层占比饼图"""
    _init_font()
    df = _load_city_df(city_name)
    if df.empty:
        return None
    counts = df['floor_level'].value_counts()

    fig, ax = plt.subplots(figsize=(7, 6))
    colors_list = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'][:len(counts)]
    wedges, texts, autotexts = ax.pie(
        counts.values, labels=counts.index, autopct='%1.1f%%', startangle=140,
        colors=colors_list, explode=[0.02] * len(counts), pctdistance=0.75)
    for at in autotexts:
        at.set_fontsize(12)
        at.set_fontweight('bold')
    centre = plt.Circle((0, 0), 0.55, fc='white')
    ax.add_artist(centre)
    ax.text(0, 0, f'{city_name}\n{len(df):,}套', ha='center', va='center',
            fontsize=12, fontweight='bold')
    ax.set_title(f'{city_name}楼层占比', fontsize=14, fontweight='bold')
    plt.tight_layout()
    return _fig_to_response(fig)


def chart_floor_avg_price(city_name):
    """⑦ 楼层均价柱状图"""
    _init_font()
    df = _load_city_df(city_name)
    if df.empty:
        return None
    stats = df.groupby('floor_level')['unit_price'].mean()
    for f in ['低楼层', '中楼层', '高楼层', '其他']:
        if f not in stats.index:
            stats[f] = 0
    stats = stats[['低楼层', '中楼层', '高楼层', '其他']]

    fig, ax = plt.subplots(figsize=(7, 5))
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    bars = ax.bar(stats.index, stats.values, color=colors, edgecolor='white', width=0.5)
    for b, v in zip(bars, stats.values):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 20,
                f'{v:,.0f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.axhline(y=df['unit_price'].mean(), color='gray', linestyle='--', linewidth=1,
               label=f'城区均价 {df["unit_price"].mean():,.0f}')
    ax.legend(fontsize=10)
    ax.set_title(f'{city_name}各楼层平均房价', fontsize=14, fontweight='bold')
    ax.set_ylabel('平均单价（元/㎡）', fontsize=11)
    plt.tight_layout()
    return _fig_to_response(fig)


def chart_decoration(city_name):
    """⑧ 装修结构分布"""
    _init_font()
    data = House.objects.filter(city=city_name) \
        .values('zhuangxiu').annotate(cnt=Count('id')).order_by('-cnt')
    if not data:
        return None
    total = sum(d['cnt'] for d in data)
    names = [d['zhuangxiu'] or '未知' for d in data]
    counts = [d['cnt'] for d in data]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(names, counts, color=sns.color_palette('Set3', len(names)), edgecolor='white')
    for b, v in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 20,
                f'{v}\n({v / total * 100:.1f}%)', ha='center', va='bottom',
                fontsize=9, fontweight='bold')
    ax.set_title(f'{city_name}装修结构分布', fontsize=14, fontweight='bold')
    ax.set_ylabel('房源数量（套）', fontsize=11)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
    plt.xticks(rotation=15, fontsize=10)
    plt.tight_layout()
    return _fig_to_response(fig)


def chart_area_distribution(city_name):
    """⑨ 面积区间分布"""
    _init_font()
    df = _load_city_df(city_name)
    if df.empty:
        return None
    order = ['<60㎡', '60-90㎡', '90-120㎡', '120-150㎡', '150-200㎡', '>200㎡']
    counts = df['area_group'].value_counts().reindex(order).fillna(0)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(range(len(counts)), counts.values, marker='s', linewidth=2.5,
            markersize=8, color='#D64045', markerfacecolor='white',
            markeredgewidth=2, markeredgecolor='#D64045')
    ax.fill_between(range(len(counts)), counts.values, alpha=0.1, color='#D64045')
    for i, (xi, yi) in enumerate(zip(counts.index, counts.values)):
        ax.annotate(f'{int(yi):,}套', (i, yi), textcoords="offset points",
                    xytext=(0, 12), ha='center', fontsize=10, fontweight='bold')
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(counts.index, fontsize=10)
    ax.set_title(f'{city_name}面积区间分布', fontsize=14, fontweight='bold')
    ax.set_ylabel('房源数量（套）', fontsize=11)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
    plt.tight_layout()
    return _fig_to_response(fig)
