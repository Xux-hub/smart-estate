"""
山东省二手房数据分析可视化
生成 10 张图表：描述性统计表 + 9 张可视化图表
"""
import os, re, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.ticker as ticker
import seaborn as sns

# ── 中文字体设置（强制清除缓存 + 指定字体文件）──
for f in os.listdir(matplotlib.get_cachedir()):
    if 'font' in f.lower():
        os.remove(os.path.join(matplotlib.get_cachedir(), f))
fp = fm.FontProperties(fname='C:/Windows/Fonts/simhei.ttf')
FONT_NAME = fp.get_name()
plt.rcParams['font.family'] = FONT_NAME
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")
# 再次覆盖（sns 会重置 font.family）
plt.rcParams['font.family'] = FONT_NAME

# ── 输出目录 ──
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shandong_charts')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 数据库连接 ──
import pymysql, yaml
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, 'config', 'database.yml'), encoding='utf-8') as f:
    cfg = yaml.safe_load(f)['database']

def get_conn():
    return pymysql.connect(
        host=cfg['host'], port=int(cfg['port']),
        user=cfg['user'], password=cfg['password'],
        database=cfg['name'], charset='utf8mb4',
    )

def load_data():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM house_info", conn)
    conn.close()
    df['price_num'] = pd.to_numeric(df['price'], errors='coerce')
    df['mianji_num'] = df['mianji'].apply(lambda v: float(re.search(r'\d+(?:\.\d+)?', str(v)).group(0)) if v and re.search(r'\d+(?:\.\d+)?', str(v)) else None)
    df['floor_level'] = df['louceng'].apply(
        lambda t: '低楼层' if t and isinstance(t, str) and t.strip().startswith('低') else
                  '中楼层' if t and isinstance(t, str) and t.strip().startswith('中') else
                  '高楼层' if t and isinstance(t, str) and t.strip().startswith('高') else '未知')
    df['listing_date'] = pd.to_datetime(df['shijian'], errors='coerce')
    intervals = [(0,60,'<60㎡'),(60,90,'60-90㎡'),(90,120,'90-120㎡'),(120,150,'120-150㎡'),(150,200,'150-200㎡'),(200,999,'>200㎡')]
    df['area_group'] = df['mianji_num'].apply(
        lambda m: next((l for lo,hi,l in intervals if lo <= (m or 0) < hi), '>200㎡') if not pd.isna(m) else '未知')
    return df

# ═══ (1) 描述性分析表（+ 彩色表格图片） ═══
def desc_stats_table(df):
    stats = df.groupby('city').agg(
        count=('price_num','count'), mean=('price_num','mean'), std=('price_num','std'),
        min=('price_num','min'), p25=('price_num',lambda x: x.quantile(0.25)),
        p50=('price_num',lambda x: x.quantile(0.50)),
        p75=('price_num',lambda x: x.quantile(0.75)), max=('price_num','max'),
    ).round(2).sort_values('mean', ascending=False)
    print("="*80 + "\n(1) 山东省各城市房价描述性分析表" + "\n" + "="*80)
    print(stats.to_string(), '\n')
    stats.to_csv(os.path.join(OUTPUT_DIR,'01_descriptive_stats.csv'), encoding='utf-8-sig')
    print("  → 已保存: 01_descriptive_stats.csv")

    # ── 生成彩色表格图片 ──
    _styled_table_image(stats)
    return stats


def _styled_table_image(stats):
    """将描述性统计表绘制为彩色图片，每列按值大小着色"""
    nrows, ncols = stats.shape
    col_names = ['count','mean','std','min','25%','50%','75%','max']
    row_names = stats.index.tolist()
    data = stats.values

    from matplotlib.colors import to_rgba
    import matplotlib.colors as mcolors

    # 每列的调色板（不同颜色区分指标类型）
    palettes = {
        'count': plt.cm.Blues,
        'mean':  plt.cm.Reds,
        'std':   plt.cm.Purples,
        'min':   plt.cm.Greens,
        '25%':   plt.cm.Oranges,
        '50%':   plt.cm.Reds,
        '75%':   plt.cm.Oranges,
        'max':   plt.cm.Reds,
    }

    fig, ax = plt.subplots(figsize=(14, 0.6 * nrows + 2.5))
    ax.axis('off')

    col_widths  = [1.2, 3.0, 3.0, 2.5, 2.5, 2.5, 2.5, 2.5, 2.8]
    row_height  = 0.55
    x_start, y_start = 0, 0

    def cell_rect(cx, cy, w, h):
        return plt.Rectangle((cx, cy), w, h, linewidth=0.8, edgecolor='white')

    # ── 绘制表头 ──
    headers = ['city'] + col_names
    for j, h in enumerate(headers):
        cx = sum(col_widths[:j])
        rect = cell_rect(cx, y_start, col_widths[j], row_height)
        rect.set_facecolor('#2C3E50')
        ax.add_patch(rect)
        ax.text(cx + col_widths[j]/2, y_start + row_height/2, h, ha='center', va='center',
                fontsize=11, fontweight='bold', color='white')

    # ── 绘制数据行 ──
    for i in range(nrows):
        y = y_start + row_height * (i + 1)
        bd_color = '#ECF0F1' if i % 2 == 0 else 'white'

        # 城市名（第一列）
        rect = cell_rect(x_start, y, col_widths[0], row_height)
        rect.set_facecolor(bd_color)
        ax.add_patch(rect)
        ax.text(x_start + col_widths[0]/2, y + row_height/2, row_names[i],
                ha='center', va='center', fontsize=10, fontweight='bold')

        # 数值列
        for j in range(ncols):
            cx = sum(col_widths[:j+1])
            val = data[i, j]
            vmin, vmax = stats[stats.columns[j]].min(), stats[stats.columns[j]].max()
            norm_val = (val - vmin) / (vmax - vmin) if vmax > vmin else 0.5
            cmap = palettes[col_names[j]]
            rgba = list(to_rgba(cmap(norm_val)))
            rgba[3] = 0.25 + 0.65 * norm_val  # 透明度 0.25~0.9
            rect = cell_rect(cx, y, col_widths[j+1], row_height)
            rect.set_facecolor(rgba)
            ax.add_patch(rect)
            ax.text(cx + col_widths[j+1]/2, y + row_height/2, f'{val:.2f}',
                    ha='center', va='center', fontsize=10,
                    color='black' if norm_val < 0.6 else 'white')

    # 调整坐标
    total_w = sum(col_widths)
    total_h = row_height * (nrows + 1)
    ax.set_xlim(0, total_w)
    ax.set_ylim(0, total_h + 0.3)
    ax.invert_yaxis()  # 让 y=0 在顶部，表头在上
    ax.set_title('山东省各城市房价描述性分析表', fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '01_descriptive_stats.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("  → 已保存: 01_descriptive_stats.png（彩色表格图片）")

# ═══ (2) 房源数量柱状图 ═══
def housing_count_bar(df):
    counts = df['city'].value_counts()
    fig, ax = plt.subplots(figsize=(12,6))
    bars = ax.bar(counts.index, counts.values, color=sns.color_palette('Blues_r', len(counts)), edgecolor='white')
    for b,v in zip(bars, counts.values):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+50, str(v), ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.set_title('山东省各城市房源数量统计', fontsize=16, fontweight='bold')
    ax.set_xlabel('城市', fontsize=12); ax.set_ylabel('房源数量（套）', fontsize=12)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x,_: f'{int(x):,}'))
    plt.xticks(rotation=30); plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR,'02_housing_count.png'), dpi=150); plt.close()
    print("  → 已保存: 02_housing_count.png")

# ═══ (3) 平均房价柱状图 ═══
def avg_price_bar(df):
    avg = df.groupby('city')['unit_price'].mean().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(12,6))
    bars = ax.bar(avg.index, avg.values, color=sns.color_palette('Reds_r', len(avg)), edgecolor='white')
    for b,v in zip(bars, avg.values):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+50, f'{v:,.0f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_title('山东省各城市平均房价统计', fontsize=16, fontweight='bold')
    ax.set_xlabel('城市', fontsize=12); ax.set_ylabel('平均单价（元/㎡）', fontsize=12)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x,_: f'{x:,.0f}'))
    plt.xticks(rotation=30); plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR,'03_avg_price.png'), dpi=150); plt.close()
    print("  → 已保存: 03_avg_price.png")

# ═══ (4) 月度挂牌趋势折线图 ═══
def listing_trend(df):
    monthly = df.dropna(subset=['listing_date']).set_index('listing_date').resample('ME').size()
    monthly.index = monthly.index.strftime('%Y-%m')
    fig, ax = plt.subplots(figsize=(14,6))
    ax.plot(monthly.index, monthly.values, marker='o', linewidth=2, markersize=6, color='#2E86AB')
    ax.fill_between(range(len(monthly)), monthly.values, alpha=0.15, color='#2E86AB')
    for i,(xi,yi) in enumerate(zip(monthly.index,monthly.values)):
        if i%3==0:
            ax.annotate(str(yi), (xi,yi), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
    ax.set_title('山东省二手房挂牌数量月度变化', fontsize=16, fontweight='bold')
    ax.set_xlabel('月份', fontsize=12); ax.set_ylabel('挂牌数量（套）', fontsize=12)
    plt.xticks(rotation=45); plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR,'04_listing_trend.png'), dpi=150); plt.close()
    print("  → 已保存: 04_listing_trend.png")

# ═══ (5) 各城市热门户型 Top5 ═══
def top5_layouts(df):
    cities = sorted(df['city'].unique())
    rows = (len(cities)+2)//3
    fig, axes = plt.subplots(rows,3,figsize=(18,5*rows))
    axes = axes.flatten()
    for i,city in enumerate(cities):
        top5 = df[df['city']==city]['huxing'].value_counts().head(5)
        axes[i].barh(top5.index[::-1], top5.values[::-1], color=sns.color_palette('Set2',5))
        axes[i].set_title(f'{city}（共{len(df[df["city"]==city])}套）', fontsize=13, fontweight='bold')
        axes[i].set_xlabel('数量')
    for j in range(i+1,len(axes)):
        axes[j].set_visible(False)
    fig.suptitle('山东省各城市热门房源户型 Top5', fontsize=18, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR,'05_top5_layouts.png'), dpi=150, bbox_inches='tight'); plt.close()
    print("  → 已保存: 05_top5_layouts.png")

# ═══ (6) 楼层占比饼图 ═══
def floor_pie(df):
    counts = df['floor_level'].value_counts()
    fig, ax = plt.subplots(figsize=(8,8))
    wedges, texts, autotexts = ax.pie(
        counts.values, labels=counts.index, autopct='%1.1f%%', startangle=140,
        colors=['#FF6B6B','#4ECDC4','#45B7D1','#96CEB4'][:len(counts)], explode=[0.02]*len(counts), pctdistance=0.78)
    for at in autotexts: at.set_fontsize(13); at.set_fontweight('bold')
    for t in texts: t.set_fontsize(13)
    ax.set_title('山东省二手房所在楼层占比', fontsize=16, fontweight='bold')
    centre = plt.Circle((0,0),0.55,fc='white'); ax.add_artist(centre)
    ax.text(0,0,f'总计\n{len(df):,}套', ha='center', va='center', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR,'06_floor_pie.png'), dpi=150); plt.close()
    print("  → 已保存: 06_floor_pie.png")

# ═══ (7) 楼层均价柱状图 ═══
def floor_avg_price(df):
    stats = df.groupby('floor_level')['unit_price'].mean()
    for f in ['低楼层','中楼层','高楼层','未知']:
        if f not in stats.index: stats[f] = 0
    stats = stats[['低楼层','中楼层','高楼层','未知']]
    fig, ax = plt.subplots(figsize=(8,6))
    bars = ax.bar(stats.index, stats.values, color=['#FF6B6B','#4ECDC4','#45B7D1','#96CEB4'], edgecolor='white', width=0.5)
    for b,v in zip(bars, stats.values):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+30, f'{v:,.0f} 元/㎡', ha='center', va='bottom', fontsize=12, fontweight='bold')
    ax.set_title('山东省各楼层平均房价', fontsize=16, fontweight='bold')
    ax.set_xlabel('楼层', fontsize=12); ax.set_ylabel('平均单价（元/㎡）', fontsize=12)
    ax.axhline(y=df['unit_price'].mean(), color='gray', linestyle='--', linewidth=1, label=f'全省均价 {df["unit_price"].mean():,.0f}')
    ax.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR,'07_floor_avg_price.png'), dpi=150); plt.close()
    print("  → 已保存: 07_floor_avg_price.png")

# ═══ (8) 装修结构柱状图 ═══
def decoration_bar(df):
    counts = df['zhuangxiu'].value_counts()
    fig, ax = plt.subplots(figsize=(12,6))
    bars = ax.bar(counts.index, counts.values, color=sns.color_palette('Set3', len(counts)), edgecolor='white')
    for b,v in zip(bars, counts.values):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+30, f'{v}\n({v/len(df)*100:.1f}%)', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_title('山东省二手房装修结构分布', fontsize=16, fontweight='bold')
    ax.set_xlabel('装修情况', fontsize=12); ax.set_ylabel('房源数量（套）', fontsize=12)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x,_: f'{int(x):,}'))
    plt.xticks(rotation=20); plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR,'08_decoration.png'), dpi=150); plt.close()
    print("  → 已保存: 08_decoration.png")

# ═══ (9) 面积区间折线图 ═══
def area_distribution(df):
    order = ['<60㎡','60-90㎡','90-120㎡','120-150㎡','150-200㎡','>200㎡']
    counts = df['area_group'].value_counts().reindex(order)
    fig, ax = plt.subplots(figsize=(10,6))
    ax.plot(counts.index, counts.values, marker='s', linewidth=2.5, markersize=10, color='#D64045', markerfacecolor='white', markeredgewidth=2.5, markeredgecolor='#D64045')
    ax.fill_between(range(len(counts)), counts.values, alpha=0.1, color='#D64045')
    for i,(xi,yi) in enumerate(zip(counts.index,counts.values)):
        ax.annotate(f'{yi:,}套', (xi,yi), textcoords="offset points", xytext=(0,15), ha='center', fontsize=11, fontweight='bold')
    ax.set_title('山东省二手房面积区间分布', fontsize=16, fontweight='bold')
    ax.set_xlabel('面积区间', fontsize=12); ax.set_ylabel('房源数量（套）', fontsize=12)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x,_: f'{int(x):,}'))
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR,'09_area_distribution.png'), dpi=150); plt.close()
    print("  → 已保存: 09_area_distribution.png")

# ═══ (10) 高端小区热词图 ═══
def high_end_communities(df):
    h = df[df['unit_price']>60000]
    if len(h)==0:
        print("  → (10) 没有单价>6万的房源"); return
    cs = h.groupby('mingcheng').agg(count=('id','count'), avg_price=('unit_price','mean')).sort_values('count',ascending=False).head(30)
    fig, ax = plt.subplots(figsize=(14,10))
    norm = plt.Normalize(cs['avg_price'].min(), cs['avg_price'].max())
    colors = plt.cm.YlOrRd(norm(cs['avg_price'].values))
    bars = ax.barh(cs.index[::-1], cs['count'].values[::-1], color=colors[::-1], edgecolor='white', height=0.7)
    for b,(_,row) in zip(bars, cs.iloc[::-1].iterrows()):
        ax.text(b.get_width()+0.3, b.get_y()+b.get_height()/2, f'{row["count"]}套 | 均价{row["avg_price"]:,.0f}元/㎡', va='center', fontsize=9)
    sm = plt.cm.ScalarMappable(cmap='YlOrRd', norm=norm); sm.set_array([])
    plt.colorbar(sm, ax=ax, shrink=0.6).set_label('平均单价（元/㎡）', fontsize=11)
    ax.set_title('山东省高端小区热词图（单价 > 6万元/㎡）', fontsize=16, fontweight='bold')
    ax.set_xlabel('房源数量（套）', fontsize=12); ax.set_ylabel('小区名称', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR,'10_high_end_communities.png'), dpi=150); plt.close()
    print("  → 已保存: 10_high_end_communities.png")

# ═══ (11) 小区热力词云图（房屋形状） ═══
def house_wordcloud(df):
    from wordcloud import WordCloud
    from PIL import Image, ImageDraw

    # 统计每个小区出现频次
    freq = df['mingcheng'].value_counts().to_dict()

    # 创建房屋形状 mask
    size = (500, 500)
    mask = Image.new('L', size, 255)
    draw = ImageDraw.Draw(mask)

    # 屋顶（三角形）
    roof_pts = [(250, 50), (400, 200), (100, 200)]
    draw.polygon(roof_pts, fill=0)

    # 房屋主体（矩形）
    draw.rectangle([100, 200, 400, 450], fill=0)

    # 门
    draw.rectangle([210, 350, 290, 450], fill=255)

    # 窗户
    draw.rectangle([130, 250, 190, 310], fill=255)
    draw.rectangle([310, 250, 370, 310], fill=255)

    mask = np.array(mask)

    # 生成词云
    wc = WordCloud(
        font_path='C:/Windows/Fonts/simhei.ttf',
        mask=mask,
        background_color='white',
        max_font_size=80,
        min_font_size=8,
        max_words=200,
        width=500, height=500,
        colormap='Set2',
        random_state=42,
    ).generate_from_frequencies(freq)

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    ax.set_title('山东省热门小区词云图', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '11_community_wordcloud.png'), dpi=200)
    plt.close()
    print("  → 已保存: 11_community_wordcloud.png（房屋形状小区词云）")


# ═══ 主函数 ═══
def main():
    print("正在加载数据...")
    df = load_data()
    print(f"  共加载 {len(df):,} 条房源数据，{df['city'].nunique()} 个城市\n")
    desc_stats_table(df)
    housing_count_bar(df)
    avg_price_bar(df)
    listing_trend(df)
    top5_layouts(df)
    floor_pie(df)
    floor_avg_price(df)
    decoration_bar(df)
    area_distribution(df)
    high_end_communities(df)
    house_wordcloud(df)
    print(f"\n所有图表已保存到: {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
