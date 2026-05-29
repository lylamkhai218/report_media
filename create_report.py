import csv
import json
import os
import sys
import glob

# Ensure console can print utf-8 characters on Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# Tự động tìm kiếm file "Tỉ lệ giữ chân..." hoặc "Tỉ lệ giữu chân..." mới nhất trong thư mục
REPORT_DIR = r"d:\T&TVina\Report"
csv_files = glob.glob(os.path.join(REPORT_DIR, "Tỉ lệ gi* chân*.csv"))

if csv_files:
    # Sắp xếp theo thời gian chỉnh sửa (mới nhất lên đầu)
    csv_files.sort(key=os.path.getmtime, reverse=True)
    CSV_PATH = csv_files[0]
else:
    CSV_PATH = os.path.join(REPORT_DIR, "Tỉ lệ giữu chân May-01-2026_May-28-2026_3422172974611676.csv")

HTML_OUTPUT = os.path.join(REPORT_DIR, "report_giu_chan.html")
CSV_OUTPUT = os.path.join(REPORT_DIR, "report_giu_chan_summary.csv")

def safe_float(val, default=0.0):
    try:
        val = val.strip().replace(',', '.')
        return float(val) if val else default
    except ValueError:
        return default

def safe_int(val, default=0):
    try:
        val = val.strip().replace(',', '').replace('.', '')
        return int(val) if val else default
    except ValueError:
        return default

def parse_csv():
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        sys.exit(1)

    posts = []
    
    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        headers = next(reader)
        
        for row_idx, row in enumerate(reader, start=2):
            if not row:
                continue
            
            # Pad row if columns are missing
            if len(row) < 155:
                row = row + [''] * (155 - len(row))
                
            post_id = row[0].strip()
            # Skip header or empty row
            if not post_id or post_id in ("ID bài viết", "Post ID", "ID"):
                continue
                
            post_type = row[11].strip() or "Unknown"
            duration = safe_float(row[5])
            views = safe_int(row[17])
            page_name = row[2].strip()
            title = row[3].strip()
            description = row[4].strip()
            
            # If title is empty, generate one from description
            if not title:
                clean_desc = description.replace('\n', ' ').strip()
                title = clean_desc[:50] + "..." if len(clean_desc) > 50 else (clean_desc or f"{post_type} {post_id}")
            
            publish_date = row[6].strip()
            permalink = row[8].strip()
            reach = safe_int(row[18])
            engagement = safe_int(row[19])
            likes = safe_int(row[20])
            comments = safe_int(row[21])
            shares = safe_int(row[22])
            clicks = safe_int(row[23])
            organic_views = safe_int(row[24])
            paid_views = safe_int(row[25])
            
            # Parse retention curves
            # Columns 56 to 96 (indices inclusive)
            ret_total = []
            for i in range(56, 97):
                ret_total.append(safe_float(row[i]))
                
            # Columns 97 to 137 (indices inclusive)
            ret_15s = []
            for i in range(97, 138):
                ret_15s.append(safe_float(row[i]))
            
            # Demographics
            demographics = {
                "M_18_24": safe_int(row[140]),
                "M_25_34": safe_int(row[141]),
                "M_35_44": safe_int(row[138]),
                "M_45_54": safe_int(row[139]),
                "M_55_64": safe_int(row[142]),
                "M_65_plus": safe_int(row[148]),
                "F_18_24": safe_int(row[146]),
                "F_25_34": safe_int(row[144]),
                "F_35_44": safe_int(row[143]),
                "F_45_54": safe_int(row[147]),
                "F_55_64": safe_int(row[145])
            }
            
            # Countries
            countries = {
                "Vietnam (VN)": safe_int(row[149]),
                "Japan (JP)": safe_int(row[150]),
                "Pakistan (PK)": safe_int(row[151]),
                "Germany (DE)": safe_int(row[152]),
                "India (IN)": safe_int(row[153]),
                "Indonesia (ID)": safe_int(row[154])
            }
            
            has_retention = any(v > 0 for v in ret_total) and (post_type == "Video" or duration > 0)
            
            # We calculate retention checkpoints at 0%, 25%, 50%, 75%, 100%
            # 0% is index 0, 25% is index 10, 50% is index 20, 75% is index 30, 100% is index 40
            ret_checkpoints = {
                "p0": ret_total[0] * 100 if has_retention else 0.0,
                "p25": ret_total[10] * 100 if has_retention else 0.0,
                "p50": ret_total[20] * 100 if has_retention else 0.0,
                "p75": ret_total[30] * 100 if has_retention else 0.0,
                "p100": ret_total[40] * 100 if has_retention else 0.0,
            }
            
            posts.append({
                "id": post_id,
                "page_name": page_name,
                "title": title,
                "description": description,
                "post_type": post_type,
                "duration": duration,
                "publish_date": publish_date,
                "permalink": permalink,
                "views": views,
                "reach": reach,
                "engagement": engagement,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "clicks": clicks,
                "organic_views": organic_views,
                "paid_views": paid_views,
                "has_retention": has_retention,
                "ret_total": ret_total,
                "ret_15s": ret_15s,
                "ret_checkpoints": ret_checkpoints,
                "demographics": demographics,
                "countries": countries
            })
            
    return posts

def generate_csv_summary(posts):
    # Sort posts by views descending
    sorted_posts = sorted(posts, key=lambda x: x['views'], reverse=True)
    
    with open(CSV_OUTPUT, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "ID Bài Viết", "Tiêu Đề", "Loại Bài Viết", "Thời Lượng (s)", "Ngày Đăng", 
            "Lượt Xem", "Lượt Tiếp Cận", "Lượt Tương Tác", 
            "Thích", "Bình Luận", "Chia Sẻ", "Lượt Click",
            "Xem Tự Nhiên", "Xem Quảng Cáo", "Có Dữ Liệu Giữ Chân",
            "Giữ Chân 0% (Bắt đầu)", "Giữ Chân 25% (Quãng 10)", 
            "Giữ Chân 50% (Quãng 20)", "Giữ Chân 75% (Quãng 30)", 
            "Giữ Chân 100% (Kết thúc)", "Đường Dẫn"
        ])
        
        for p in sorted_posts:
            cp = p['ret_checkpoints']
            writer.writerow([
                p['id'], p['title'], p['post_type'], p['duration'] if p['post_type'] == "Video" else "-", p['publish_date'],
                p['views'], p['reach'], p['engagement'],
                p['likes'], p['comments'], p['shares'], p['clicks'],
                p['organic_views'], p['paid_views'], "Có" if p['has_retention'] else "Không",
                f"{cp['p0']:.1f}%" if p['has_retention'] else "-",
                f"{cp['p25']:.1f}%" if p['has_retention'] else "-", 
                f"{cp['p50']:.1f}%" if p['has_retention'] else "-", 
                f"{cp['p75']:.1f}%" if p['has_retention'] else "-", 
                f"{cp['p100']:.1f}%" if p['has_retention'] else "-",
                p['permalink']
            ])
            
    print(f"Generated CSV summary: {CSV_OUTPUT}")

def generate_html_report(posts):
    # Calculate global metrics
    total_views = sum(p['views'] for p in posts)
    total_reach = sum(p['reach'] for p in posts)
    total_engagement = sum(p['engagement'] for p in posts)
    
    # Avg duration only for video posts
    video_posts = [p for p in posts if p['post_type'] == "Video" or p['duration'] > 0]
    total_duration = sum(p['duration'] for p in video_posts)
    avg_duration = total_duration / len(video_posts) if video_posts else 0.0
    
    # Sort posts by views
    sorted_by_views = sorted(posts, key=lambda x: x['views'], reverse=True)
    top_viewed = sorted_by_views[0] if sorted_by_views else None
    
    # Sort by retention at 50% (among those that have retention data)
    posts_with_ret = [p for p in posts if p['has_retention']]
    top_ret_50 = sorted(posts_with_ret, key=lambda x: x['ret_checkpoints']['p50'], reverse=True)[0] if posts_with_ret else None
    top_ret_100 = sorted(posts_with_ret, key=lambda x: x['ret_checkpoints']['p100'], reverse=True)[0] if posts_with_ret else None
    
    # Pre-formatted numbers for offline preview support (fallback when JS/Tailwind CDN is blocked)
    total_views_fmt = f"{total_views:,}".replace(",", ".")
    total_engagement_fmt = f"{total_engagement:,}".replace(",", ".")
    avg_duration_fmt = f"{avg_duration:.1f}"
    
    eng_rate = (total_engagement / total_views * 100) if total_views > 0 else 0.0
    eng_rate_fmt = f"{eng_rate:.1f}"
    
    top_ret_50_val_fmt = f"{top_ret_50['ret_checkpoints']['p50']:.1f}%" if top_ret_50 else "-"
    top_ret_50_title = top_ret_50['title'] if top_ret_50 else "-"
    
    top_ret_100_val_fmt = f"{top_ret_100['ret_checkpoints']['p100']:.1f}%" if top_ret_100 else "-"
    top_ret_100_title = top_ret_100['title'] if top_ret_100 else "-"
    
    # Pre-render table rows in Python
    table_rows_html = ""
    for p in sorted_by_views:
        is_video = p['post_type'] == 'Video'
        duration_text = f"{int(p['duration'] // 60)}m {int(p['duration'] % 60)}s" if is_video else "-"
        
        ret25_text = f"{p['ret_checkpoints']['p25']:.1f}%" if (p['has_retention'] and is_video) else "-"
        ret50_text = f"{p['ret_checkpoints']['p50']:.1f}%" if (p['has_retention'] and is_video) else "-"
        ret100_text = f"{p['ret_checkpoints']['p100']:.1f}%" if (p['has_retention'] and is_video) else "-"
        
        badge_class = "badge-video"
        if p['post_type'] == 'Video':
            badge_class = "badge-video"
        elif p['post_type'] in ('Photo', 'Ảnh'):
            badge_class = "badge-photo"
        elif p['post_type'] in ('Shared link', 'Liên kết chia sẻ'):
            badge_class = "badge-link"
            
        type_label = p['post_type']
        if type_label == 'Photo':
            type_label = 'Hình ảnh'
        elif type_label == 'Shared link':
            type_label = 'Liên kết'
            
        views_cell = f"{p['views']:,}".replace(",", ".")
        eng_cell = f"{p['engagement']:,}".replace(",", ".")
        
        table_rows_html += f"""
        <tr class="hover:bg-gray-800/40 transition-colors border-b border-gray-800/50">
            <td class="py-4 px-4 font-bold text-white max-w-[280px] truncate" title="{p['title']}">
                <div class="flex items-center" style="display: flex; align-items: center;">
                    <span class="badge {badge_class} mr-2 shadow-sm" style="margin-right: 8px;">{type_label}</span>
                    <span class="truncate text-[13px] md:text-sm font-semibold">{p['title']}</span>
                </div>
            </td>
            <td class="py-4 px-3 text-center text-gray-300 font-semibold text-[13px] md:text-sm">{duration_text}</td>
            <td class="py-4 px-3 text-right font-bold text-white text-[13px] md:text-sm">{views_cell}</td>
            <td class="py-4 px-3 text-right text-gray-300 font-semibold text-[13px] md:text-sm">{eng_cell}</td>
            <td class="py-4 px-3 text-right font-extrabold text-indigo-300 text-[13px] md:text-sm">{ret25_text}</td>
            <td class="py-4 px-3 text-right font-extrabold text-purple-300 text-[13px] md:text-sm">{ret50_text}</td>
            <td class="py-4 px-3 text-right font-extrabold text-emerald-300 text-[13px] md:text-sm">{ret100_text}</td>
            <td class="py-4 px-4 text-center">
                <a href="{p['permalink']}" target="_blank" class="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/25 rounded hover:bg-indigo-500 hover:text-white transition-colors duration-200 shadow-sm">
                    Chi tiết ↗
                </a>
            </td>
        </tr>
        """
        
    # Pre-render dropdown options
    primary_options_html = ""
    secondary_options_html = f'<option value="" data-i18n="chart_compare">-- So sánh với... --</option>\n'
    for p in posts_with_ret:
        title_trunc = p['title'][:35] + "..." if len(p['title']) > 35 else p['title']
        views_opt = f"{p['views']:,}".replace(",", ".")
        primary_options_html += f'<option value="{p["id"]}">{title_trunc} ({views_opt} views)</option>\n'
        secondary_options_html += f'<option value="{p["id"]}">{title_trunc} ({views_opt} views)</option>\n'

    # Demographics & Geography Data
    demo_totals = {
        "M_18_24": 0, "M_25_34": 0, "M_35_44": 0, "M_45_54": 0, "M_55_64": 0, "M_65_plus": 0,
        "F_18_24": 0, "F_25_34": 0, "F_35_44": 0, "F_45_54": 0, "F_55_64": 0
    }
    country_totals = {
        "Vietnam (VN)": 0, "Japan (JP)": 0, "Pakistan (PK)": 0, "Germany (DE)": 0, "India (IN)": 0, "Indonesia (ID)": 0
    }
    
    for p in posts:
        for k, v in p['demographics'].items():
            demo_totals[k] += v
        for k, v in p['countries'].items():
            country_totals[k] += v
            
    # Calculate average retention curve across all videos
    avg_ret_curve = [0.0] * 41
    if posts_with_ret:
        for i in range(41):
            avg_ret_curve[i] = sum(p['ret_total'][i] for p in posts_with_ret) / len(posts_with_ret) * 100

    # Pre-render Fallback HTML chart bars (21 bars representing the first video curve)
    fallback_chart_bars_html = ""
    primary_post = posts_with_ret[0] if posts_with_ret else None
    if primary_post:
        ret_data = primary_post['ret_total']
        for i in range(0, 41, 2):
            val = ret_data[i] * 100
            fallback_chart_bars_html += f"""
            <div class="fallback-bar-wrapper" style="display:flex; flex-direction:column; align-items:center; flex:1; height:100%; justify-content:flex-end; position:relative;">
                <div class="fallback-bar" style="height: {val:.0f}%; width: 55%; background: linear-gradient(180deg, #6366f1 0%, rgba(99,102,241,0.2) 100%); border-radius: 2px 2px 0 0;"></div>
                <span style="font-size: 8px; color: #6b7280; margin-top: 4px;">Q{i}</span>
            </div>
            """

    # Pre-render Fallback Audience List (Top demographics groups)
    fallback_audience_html = ""
    sorted_demo = sorted(demo_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    max_demo_val = max(demo_totals.values()) if demo_totals.values() else 1
    for key, val in sorted_demo:
        gender = "Nam" if key.startswith('M') else "Nữ"
        age = key.replace('M_', '').replace('F_', '').replace('_plus', '+').replace('_', '-')
        pct = (val / max_demo_val) * 100 if max_demo_val > 0 else 0
        fallback_audience_html += f"""
        <div style="display: flex; flex-direction: column; gap: 4px; width: 100%;">
            <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: bold; color: #d1d5db;">
                <span>{gender}, {age} tuổi</span>
                <span>{val:,} lượt</span>
            </div>
            <div style="background-color: rgba(255,255,255,0.05); height: 8px; border-radius: 4px; overflow: hidden; width: 100%;">
                <div style="background-color: #818cf8; height: 100%; width: {pct:.0f}%; border-radius: 4px;"></div>
            </div>
        </div>
        """
            
    # Prepare data JSON for injection
    report_data = {
        "posts": posts,
        "summary": {
            "total_posts": len(posts),
            "total_views": total_views,
            "total_reach": total_reach,
            "total_engagement": total_engagement,
            "avg_duration": round(avg_duration, 1),
            "top_viewed": top_viewed['title'] if top_viewed else "N/A",
            "top_viewed_views": top_viewed['views'] if top_viewed else 0,
            "top_ret_50": top_ret_50['title'] if top_ret_50 else "N/A",
            "top_ret_50_val": round(top_ret_50['ret_checkpoints']['p50'], 1) if top_ret_50 else 0.0,
            "top_ret_100": top_ret_100['title'] if top_ret_100 else "N/A",
            "top_ret_100_val": round(top_ret_100['ret_checkpoints']['p100'], 1) if top_ret_100 else 0.0
        },
        "demo_totals": demo_totals,
        "country_totals": country_totals,
        "avg_ret_curve": avg_ret_curve
    }
    
    data_json = json.dumps(report_data, ensure_ascii=False)
    
    html_template = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Báo cáo Tỉ lệ Giữ chân Video - Murrplastik VN</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Google Fonts Inter (High legibility for screen sharing) -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* Force border-box model globally to prevent horizontal scroll stretching */
        *, *::before, *::after {
            box-sizing: border-box !important;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #080c14;
            color: #ffffff;
            margin: 0;
            padding: 0;
            letter-spacing: -0.011em;
            width: 100%;
            overflow-x: hidden; /* Avoid side scrolling */
        }
        
        header {
            background-color: #0d1321;
            border-bottom: 1px solid #1f2937;
            padding: 20px 16px;
            width: 100%;
        }
        
        .header-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
            width: 100%;
        }
        @media (min-width: 768px) {
            .header-container {
                flex-direction: row;
                justify-content: space-between;
                align-items: center;
            }
        }
        
        main {
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px 16px;
            width: 100%;
        }
        
        .grid-kpis {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
            margin-bottom: 32px;
            width: 100%;
        }
        @media (min-width: 640px) {
            .grid-kpis { grid-template-columns: repeat(2, 1fr); }
        }
        @media (min-width: 1024px) {
            .grid-kpis { grid-template-columns: repeat(4, 1fr); }
        }
        
        .grid-charts {
            display: grid;
            grid-template-columns: 1fr;
            gap: 24px;
            margin-bottom: 32px;
            width: 100%;
        }
        @media (min-width: 1024px) {
            .grid-charts { grid-template-columns: 2fr 1fr; }
        }
        
        .card {
            background-color: rgba(19, 26, 42, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            position: relative;
            min-width: 0; /* Keep items from pushing width */
            width: 100%;
        }
        
        .chart-controls {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 12px;
            width: 100%;
        }
        @media (min-width: 768px) {
            .chart-controls {
                flex-direction: row;
                margin-top: 0;
            }
        }
        
        select {
            background-color: #1f2937;
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid #374151;
            font-size: 12px;
            max-width: 100%;
            width: 100%;
            text-overflow: ellipsis;
            white-space: nowrap;
            overflow: hidden;
            display: block;
        }
        
        .table-container {
            overflow-x: auto;
            border: 1px solid #1f2937;
            border-radius: 12px;
            background-color: rgba(19, 26, 42, 0.5);
            margin-top: 16px;
            width: 100%;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }
        
        th, td {
            padding: 14px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        th {
            background-color: #0d1321;
            color: #9ca3af;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        td {
            font-size: 14px;
            max-width: 280px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .badge {
            display: inline-block;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 700;
            border-radius: 4px;
            white-space: nowrap;
        }
        .badge-video { background-color: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.25); }
        .badge-photo { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.25); }
        .badge-link { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.25); }
        
        .fallback-chart-container {
            display: flex;
            align-items: flex-end;
            gap: 4px;
            height: 250px;
            background: rgba(8, 12, 20, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 16px 8px;
            border-radius: 8px;
            width: 100%;
        }

        .fallback-list-container {
            display: flex; 
            flex-direction: column; 
            gap: 12px; 
            padding: 10px 0;
            width: 100%;
        }

        .custom-scrollbar::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.01);
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 99px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.35);
        }
        
        /* Desktop sticky positioning */
        .sticky-th {
            position: relative;
            background-color: #0d1321;
        }
        @media (min-width: 768px) {
            .table-container {
                overflow: visible;
            }
            .sticky-th {
                position: sticky;
                top: 85px;
                z-index: 10;
                box-shadow: 0 1px 0 0 rgba(255, 255, 255, 0.09);
            }
        }
    </style>
</head>
<body class="min-h-screen">

    <!-- Header -->
    <header class="border-b border-gray-800 bg-[#0d1321] py-5 px-4 md:px-8 md:sticky md:top-0 z-50 shadow-md">
        <div class="header-container max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div class="flex items-center gap-3" style="display: flex; align-items: center; gap: 12px;">
                <div class="w-11 h-11 bg-indigo-600 rounded-lg flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20 text-xl" style="width: 44px; height: 44px; border-radius: 8px; background-color: #4f46e5; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0;">MP</div>
                <div>
                    <h1 class="text-xl md:text-2xl font-extrabold tracking-tight text-white" style="margin:0; font-size: 20px; font-weight: 800;" data-i18n="title">PHÂN TÍCH HIỆU QUẢ TRUYỀN THÔNG</h1>
                    <p class="text-xs md:text-sm text-gray-400 font-medium" style="margin:0; color:#9ca3af; font-size: 13px;" data-i18n="subtitle">Murrplastik Việt Nam · Báo cáo từ May-01-2026 đến May-28-2026</p>
                </div>
            </div>
            
            <div class="flex flex-wrap items-center gap-3 w-full md:w-auto justify-between md:justify-end" style="display: flex; align-items: center; gap: 12px;">
                <!-- Cần gạt ngôn ngữ -->
                <div class="flex items-center gap-2.5 bg-gray-900/80 px-3.5 py-2 rounded-full border border-gray-700 select-none shadow-inner" style="display: flex; align-items: center; gap: 10px; background-color: #111827; padding: 6px 14px; border-radius: 9999px; border: 1px solid #374151;">
                    <span id="lang-label-vi" class="text-xs font-bold text-indigo-400 cursor-pointer" style="font-size: 12px; cursor: pointer; color: #818cf8; font-weight: 700;" onclick="setLanguage('vi')">VI</span>
                    <button id="lang-switch-btn" class="relative inline-flex h-5.5 w-10 items-center rounded-full bg-gray-700 transition-colors focus:outline-none" style="position: relative; width: 40px; height: 22px; border-radius: 9999px; background-color: #4b5563; border: none; cursor: pointer;" onclick="toggleLanguage()">
                        <span id="lang-dot" class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform translate-x-1 shadow-md" style="display: inline-block; width: 16px; height: 16px; border-radius: 9999px; background-color: white; transform: translateX(4px); transition: transform 0.2s;"></span>
                    </button>
                    <span id="lang-label-en" class="text-xs font-semibold text-gray-400 cursor-pointer" style="font-size: 12px; cursor: pointer; color: #9ca3af;" onclick="setLanguage('en')">EN</span>
                </div>

                <div class="flex items-center gap-2" style="display: flex; align-items: center; gap: 8px;">
                    <span class="px-3.5 py-1.5 bg-green-500/10 text-green-400 rounded-full text-xs font-bold border border-green-500/25 flex items-center gap-1.5 shadow-sm" style="background-color: rgba(16,185,129,0.1); color:#34d399; padding: 6px 14px; border-radius: 9999px; font-size: 12px; border: 1px solid rgba(16,185,129,0.25);">
                        <span class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" style="display:inline-block; width:6px; height:6px; border-radius:9999px; background-color:#34d399;"></span>
                        <span data-i18n="status">Hoàn tất</span>
                    </span>
                    <span class="text-xs text-gray-400 font-medium bg-gray-900/60 px-2.5 py-1.5 rounded border border-gray-800" style="font-size:12px; color:#9ca3af; background-color: rgba(17,24,39,0.6); padding:6px 10px; border-radius:4px; border: 1px solid #1f2937;"><span data-i18n="updated">Cập nhật:</span> 29/05/2026</span>
                </div>
            </div>
        </div>
    </header>

    <!-- iOS Document QuickLook / Standalone warning -->
    <div id="js-warning" style="background-color: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.25); color: #f87171; padding: 14px 16px; border-radius: 8px; margin: 16px 16px 0 16px; font-size: 13px; font-weight: bold; line-height: 1.5; max-width: 1200px;">
        💡 <strong>Mẹo xem trên điện thoại:</strong> Nếu không thấy biểu đồ tương tác hiển thị, bạn hãy nhấn nút <strong>Chia sẻ (biểu tượng Hộp có mũi tên [↑] ở dưới cùng màn hình)</strong> rồi chọn <strong>"Mở bằng Safari"</strong> hoặc <strong>"Mở bằng Chrome"</strong> để xem báo cáo tối ưu nhất!
    </div>

    <main class="max-w-7xl mx-auto px-4 py-8 md:px-8">

        <!-- KPI Cards Grid (Pre-rendered for robust offline view) -->
        <section class="grid-kpis grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
            <!-- Card 1 -->
            <div class="card glass-panel rounded-xl p-5 shadow-xl relative overflow-hidden group hover:scale-[1.02] transition-transform duration-300">
                <div class="text-gray-400 text-xs font-bold tracking-wider uppercase mb-1" style="color:#9ca3af; font-size:11px;" data-i18n="kpi_views">Tổng Số Lượt Xem</div>
                <div class="text-3xl md:text-4xl font-black tracking-tight text-white mb-2" style="font-size: 30px; font-weight: 900; margin: 4px 0;" id="kpi-total-views">{TOTAL_VIEWS_FMT}</div>
                <div class="text-xs text-gray-400 font-semibold flex items-center gap-1" style="color:#9ca3af; font-size: 12px;">
                    <span class="text-indigo-400 font-extrabold text-sm" style="color:#818cf8; font-weight: 800;" id="kpi-avg-duration">{AVG_DURATION_FMT}</span>s <span data-i18n="kpi_views_sub">thời lượng TB</span>
                </div>
            </div>
            <!-- Card 2 -->
            <div class="card glass-panel rounded-xl p-5 shadow-xl relative overflow-hidden group hover:scale-[1.02] transition-transform duration-300">
                <div class="text-gray-400 text-xs font-bold tracking-wider uppercase mb-1" style="color:#9ca3af; font-size:11px;" data-i18n="kpi_eng">Lượt Tương Tác</div>
                <div class="text-3xl md:text-4xl font-black tracking-tight text-white mb-2" style="font-size: 30px; font-weight: 900; margin: 4px 0;" id="kpi-total-engagement">{TOTAL_ENGAGEMENT_FMT}</div>
                <div class="text-xs text-gray-400 font-semibold flex items-center gap-1" style="color:#9ca3af; font-size: 12px;">
                    <span data-i18n="kpi_eng_sub">Tỷ lệ tương tác</span> <span class="text-purple-400 font-extrabold text-sm" style="color:#c084fc; font-weight: 800;" id="kpi-engagement-rate">{ENG_RATE_FMT}%</span>
                </div>
            </div>
            <!-- Card 3 -->
            <div class="card glass-panel rounded-xl p-5 shadow-xl relative overflow-hidden group hover:scale-[1.02] transition-transform duration-300">
                <div class="text-gray-400 text-xs font-bold tracking-wider uppercase mb-1" style="color:#9ca3af; font-size:11px;" data-i18n="kpi_ret50">Giữ Chân Top (50% video)</div>
                <div class="text-3xl md:text-4xl font-black tracking-tight text-pink-400 mb-2" style="font-size: 30px; font-weight: 900; margin: 4px 0; color:#f472b6;" id="kpi-ret-50">{TOP_RET_50_VAL_FMT}</div>
                <div class="text-xs text-gray-300 font-semibold truncate" style="color:#d1d5db; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" id="kpi-ret-50-title" title="{TOP_RET_50_TITLE}">{TOP_RET_50_TITLE}</div>
            </div>
            <!-- Card 4 -->
            <div class="card glass-panel rounded-xl p-5 shadow-xl relative overflow-hidden group hover:scale-[1.02] transition-transform duration-300">
                <div class="text-gray-400 text-xs font-bold tracking-wider uppercase mb-1" style="color:#9ca3af; font-size:11px;" data-i18n="kpi_ret100">Giữ Chân Top (Cuối video)</div>
                <div class="text-3xl md:text-4xl font-black tracking-tight text-emerald-400 mb-2" style="font-size: 30px; font-weight: 900; margin: 4px 0; color:#34d399;" id="kpi-ret-100">{TOP_RET_100_VAL_FMT}</div>
                <div class="text-xs text-gray-300 font-semibold truncate" style="color:#d1d5db; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" id="kpi-ret-100-title" title="{TOP_RET_100_TITLE}">{TOP_RET_100_TITLE}</div>
            </div>
        </section>

        <!-- Main Charts Section -->
        <section class="grid-charts grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <!-- Left Chart: Retention Curve -->
            <div class="card glass-panel rounded-xl p-5 col-span-2 shadow-2xl">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-5 border-b border-gray-800 pb-4" style="display:flex; flex-direction:column; border-bottom: 1px solid #1f2937; padding-bottom: 16px; margin-bottom: 20px; width: 100%;">
                    <div>
                        <h3 class="text-lg md:text-xl font-bold text-white" style="margin:0; font-size: 18px;" data-i18n="chart_ret_title">Biểu Đồ Tỉ Lệ Giữ Chân Khán Giả</h3>
                        <p class="text-xs md:text-sm text-gray-400 font-medium" style="margin:0; color:#9ca3af; font-size: 13px;" data-i18n="chart_ret_sub">Xem diễn biến lượt xem qua 40 điểm mốc thời gian từ đầu đến cuối video</p>
                    </div>
                    <div class="chart-controls" style="width: 100%;">
                        <select id="video-select-primary">
                            {PRIMARY_OPTIONS_HTML}
                        </select>
                        <select id="video-select-secondary">
                            {SECONDARY_OPTIONS_HTML}
                        </select>
                    </div>
                </div>
                
                <div class="h-[360px] w-full relative" style="height: 360px; position: relative; width: 100%;">
                    <!-- Fallback HTML chart (Visible when JS/Canvas is blocked) -->
                    <div id="fallback-retention-chart" class="fallback-chart-container">
                        {FALLBACK_CHART_BARS}
                    </div>
                    <!-- Interactive canvas (Hidden by default, displayed via JS) -->
                    <canvas id="retentionChart" style="display: none;"></canvas>
                </div>
                
                <div class="mt-4 text-xs text-gray-400 font-semibold flex flex-col gap-y-1.5 bg-gray-900/50 p-3 rounded-lg border border-gray-800" style="margin-top: 16px; background-color: rgba(17,24,39,0.5); padding: 12px; border-radius: 8px; border: 1px solid #1f2937; width: 100%;">
                    <span data-i18n="chart_tip">💡 <strong>Mẹo:</strong> 40 điểm quãng biểu thị thời gian video được phân bổ đều từ 0% đến 100%.</span>
                    <span data-i18n="chart_avg_note">📈 Đường nét đứt biểu thị tỉ lệ giữ chân trung bình của tất cả video.</span>
                </div>
            </div>

            <!-- Right Chart: Demographics & Geography -->
            <div class="card glass-panel rounded-xl p-5 shadow-2xl flex flex-col justify-between" style="display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div class="flex items-center justify-between border-b border-gray-800 pb-4 mb-4" style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1f2937; padding-bottom:16px; margin-bottom:16px;">
                        <h3 class="text-lg md:text-xl font-bold text-white" style="margin:0; font-size:18px;" data-i18n="audience_title">Phân Khúc Khán Giả</h3>
                        <div class="flex gap-1.5" style="display:flex; gap:6px;">
                            <button id="tab-demo-btn" class="px-3 py-1.5 text-xs font-bold bg-indigo-600 text-white rounded-lg transition-colors" style="background-color: #4f46e5; color: white; padding: 6px 12px; border-radius: 6px; border: none; font-size: 11px; cursor: pointer;" data-i18n="audience_demo_btn">Độ tuổi/Giới tính</button>
                            <button id="tab-geo-btn" class="px-3 py-1.5 text-xs font-bold bg-gray-800 text-gray-300 hover:bg-gray-700 rounded-lg transition-colors" style="background-color: #374151; color: #d1d5db; padding: 6px 12px; border-radius: 6px; border: none; font-size: 11px; cursor: pointer;" data-i18n="audience_geo_btn">Quốc gia</button>
                        </div>
                    </div>
                    
                    <div class="h-[280px] w-full relative" style="height: 280px; position: relative; width: 100%;" id="audience-chart-container">
                        <!-- Fallback list for offline view -->
                        <div id="fallback-audience-list" class="fallback-list-container">
                            {FALLBACK_AUDIENCE_HTML}
                        </div>
                        <!-- Interactive Canvas -->
                        <canvas id="audienceChart" style="display: none;"></canvas>
                    </div>
                </div>

                <div class="border-t border-gray-800 pt-4 mt-4 text-sm font-semibold text-gray-300 bg-gray-900/30 p-3 rounded-lg border border-gray-850" style="margin-top:16px; border-top:1px solid #1f2937; background-color: rgba(17,24,39,0.3); padding:12px; border-radius:8px;">
                    <div class="flex justify-between mb-1.5" style="display:flex; justify-content:space-between; margin-bottom:6px;">
                        <span data-i18n="audience_top_age" class="text-gray-400" style="color:#9ca3af;">Độ tuổi hàng đầu:</span>
                        <span class="text-white font-bold" id="audience-top-value">-</span>
                    </div>
                    <div class="flex justify-between" style="display:flex; justify-content:space-between;">
                        <span data-i18n="audience_top_country" class="text-gray-400" style="color:#9ca3af;">Quốc gia hàng đầu:</span>
                        <span class="text-white font-bold" id="audience-top-second-value">Vietnam (VN)</span>
                    </div>
                </div>
            </div>
        </section>

        <!-- Video Leaderboard & Performance Section -->
        <section class="card glass-panel rounded-xl p-6 shadow-2xl">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-5 mb-5" style="display:flex; flex-direction:column; border-bottom:1px solid #1f2937; padding-bottom:16px; margin-bottom:16px;">
                <div>
                    <h3 class="text-lg md:text-xl font-bold text-white" style="margin:0; font-size:18px;" data-i18n="table_title">Bảng Xếp Hạng Hiệu Quả Truyền Thông</h3>
                    <p class="text-xs md:text-sm text-gray-400 font-medium" style="margin:0; color:#9ca3af; font-size: 13px;" data-i18n="table_sub">Danh sách tổng hợp hiệu quả và tỉ lệ giữ chân chi tiết</p>
                </div>
                <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full md:w-auto" style="display:flex; flex-direction:column; gap:12px; margin-top:12px;">
                    <input type="text" id="table-search" placeholder="Tìm kiếm bài viết..." class="bg-gray-800 text-sm text-white font-semibold border border-gray-700 rounded-lg px-4 py-2.5 focus:outline-none focus:border-indigo-500 w-full sm:w-64" style="background-color:#1f2937; border: 1px solid #374151; padding: 10px 16px; border-radius: 8px; color: white; font-size: 14px;">
                    <div class="flex items-center gap-1.5 self-stretch sm:self-auto" style="display:flex; gap:6px;">
                        <button id="sort-views-btn" class="flex-1 sm:flex-none px-3.5 py-2.5 text-xs font-bold bg-indigo-600 text-white rounded-lg transition-colors" style="flex:1; background-color: #4f46e5; color: white; padding: 10px 14px; border-radius: 8px; border:none; font-size:12px; font-weight:700; cursor:pointer;" data-i18n="table_sort_views">Xem nhiều nhất</button>
                        <button id="sort-ret-btn" class="flex-1 sm:flex-none px-3.5 py-2.5 text-xs font-bold bg-gray-800 text-gray-300 hover:bg-gray-700 rounded-lg transition-colors" style="flex:1; background-color: #374151; color: #d1d5db; padding: 10px 14px; border-radius: 8px; border:none; font-size:12px; font-weight:700; cursor:pointer;" data-i18n="table_sort_ret">Giữ Chân 50%</button>
                    </div>
                </div>
            </div>

            <!-- Table Container (Horizontal scroll on mobile, visible on desktop for sticky headers) -->
            <div class="table-container custom-scrollbar border border-gray-800 rounded-lg bg-gray-950/20">
                <table class="w-full text-left text-sm text-gray-200 border-collapse">
                    <thead>
                        <tr class="border-b border-gray-850">
                            <th class="sticky-th py-3.5 px-4 font-bold text-white text-xs uppercase tracking-wider min-w-[240px]" data-i18n="th_title">Tiêu Đề Bài Viết</th>
                            <th class="sticky-th py-3.5 px-3 text-center font-bold text-white text-xs uppercase tracking-wider min-w-[110px]" data-i18n="th_duration">Thời Lượng</th>
                            <th class="sticky-th py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[110px]" data-i18n="th_views">Lượt Xem</th>
                            <th class="sticky-th py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[110px]" data-i18n="th_eng">Tương Tác</th>
                            <th class="sticky-th py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[125px]" data-i18n="th_ret25">Giữ Chân 25%</th>
                            <th class="sticky-th py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[125px]" data-i18n="th_ret50">Giữ Chân 50%</th>
                            <th class="sticky-th py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[125px]" data-i18n="th_ret100">Giữ Chân 100%</th>
                            <th class="sticky-th py-3.5 px-4 text-center font-bold text-white text-xs uppercase tracking-wider min-w-[100px]" data-i18n="th_link">Liên Kết</th>
                        </tr>
                    </thead>
                    <tbody id="video-table-body" class="divide-y divide-gray-800 bg-[#090d16]/30">
                        {TABLE_ROWS_HTML}
                    </tbody>
                </table>
            </div>
            
            <div class="mt-4 text-xs font-semibold text-gray-400 flex justify-between items-center" id="table-meta">
                <span>Hiển thị {TOTAL_POSTS} trên tổng số {TOTAL_POSTS} bài viết.</span>
            </div>
        </section>

    </main>

    <!-- Data Injection -->
    <script>
        // Clean up fallback displays and toggle on active canvases
        const warningEl = document.getElementById('js-warning');
        if (warningEl) warningEl.style.display = 'none';
        
        const fallbackRetChart = document.getElementById('fallback-retention-chart');
        if (fallbackRetChart) fallbackRetChart.style.display = 'none';
        
        const mainRetCanvas = document.getElementById('retentionChart');
        if (mainRetCanvas) mainRetCanvas.style.display = 'block';
        
        const fallbackAudList = document.getElementById('fallback-audience-list');
        if (fallbackAudList) fallbackAudList.style.display = 'none';
        
        const mainAudCanvas = document.getElementById('audienceChart');
        if (mainAudCanvas) mainAudCanvas.style.display = 'block';

        const db = __REPORT_DATA__;
        let currentLang = 'vi';

        // Translation Dictionary
        const i18n = {
            vi: {
                title: "PHÂN TÍCH HIỆU QUẢ TRUYỀN THÔNG",
                subtitle: "Murrplastik Việt Nam · Báo cáo từ May-01-2026 đến May-28-2026",
                status: "Hoàn tất",
                updated: "Cập nhật:",
                kpi_views: "Tổng Số Lượt Xem",
                kpi_views_sub: "thời lượng TB",
                kpi_eng: "Lượt Tương Tác",
                kpi_eng_sub: "Tỷ lệ tương tác",
                kpi_ret50: "Giữ Chân Top (50% video)",
                kpi_ret100: "Giữ Chân Top (Cuối video)",
                chart_ret_title: "Biểu Đồ Tỉ Lệ Giữ Chân Khán Giả",
                chart_ret_sub: "Xem diễn biến lượt xem qua 40 điểm mốc thời gian từ đầu đến cuối video",
                chart_compare: "-- So sánh với... --",
                chart_tip: "💡 <strong>Mẹo:</strong> 40 điểm quãng biểu thị thời gian video được phân bổ đều từ 0% đến 100%.",
                chart_avg_note: "📈 Đường nét đứt biểu thị tỉ lệ giữ chân trung bình của tất cả video.",
                audience_title: "Phân Khúc Khán Giả",
                audience_demo_btn: "Độ tuổi/Giới tính",
                audience_geo_btn: "Quốc gia",
                audience_top_age: "Độ tuổi hàng đầu:",
                audience_top_country: "Quốc gia hàng đầu:",
                gender_male: "Nam",
                gender_female: "Nữ",
                table_title: "Bảng Xếp Hạng Hiệu Quả Truyền Thông",
                table_sub: "Danh sách tổng hợp hiệu quả và tỉ lệ giữ chân chi tiết",
                table_search: "Tìm kiếm bài viết...",
                table_sort_views: "Xem nhiều nhất",
                table_sort_ret: "Giữ Chân 50%",
                th_title: "Tiêu Đề Bài Viết",
                th_duration: "Thời Lượng",
                th_views: "Lượt Xem",
                th_eng: "Tương Tác",
                th_ret25: "Giữ Chân 25%",
                th_ret50: "Giữ Chân 50%",
                th_ret100: "Giữ Chân 100%",
                th_link: "Liên Kết",
                btn_details: "Chi tiết ↗",
                table_meta: "Hiển thị {shown} trên tổng số {total} bài viết.",
                chart_avg_label: "Trung bình tất cả",
                male_label: "Nam",
                female_label: "Nữ",
                age_suffix: " tuổi"
            },
            en: {
                title: "MEDIA PERFORMANCE ANALYSIS",
                subtitle: "Murrplastik Vietnam · Report from May-01-2026 to May-28-2026",
                status: "Completed",
                updated: "Updated:",
                kpi_views: "Total Views",
                kpi_views_sub: "avg duration",
                kpi_eng: "Total Engagements",
                kpi_eng_sub: "Engagement rate",
                kpi_ret50: "Top Retention (50% video)",
                kpi_ret100: "Top Retention (End of video)",
                chart_ret_title: "Audience Retention Curve",
                chart_ret_sub: "Watch views progression across 40 checkpoints from start to finish",
                chart_compare: "-- Compare with... --",
                chart_tip: "💡 <strong>Tip:</strong> The 40 checkpoints represent video length distributed from 0% to 100%.",
                chart_avg_note: "📈 The dashed line represents the average retention rate of all videos.",
                audience_title: "Audience Segments",
                audience_demo_btn: "Age & Gender",
                audience_geo_btn: "Countries",
                audience_top_age: "Top Age Group:",
                audience_top_country: "Top Country:",
                gender_male: "Male",
                gender_female: "Female",
                table_title: "Media Performance Leaderboard",
                table_sub: "Comprehensive ranking of post metrics and retention checkpoints",
                table_search: "Search posts...",
                table_sort_views: "Most Viewed",
                table_sort_ret: "50% Retention",
                th_title: "Post Title",
                th_duration: "Duration",
                th_views: "Views",
                th_eng: "Engagement",
                th_ret25: "25% Retention",
                th_ret50: "50% Retention",
                th_ret100: "100% Retention",
                th_link: "Link",
                btn_details: "Details ↗",
                table_meta: "Showing {shown} of {total} posts.",
                chart_avg_label: "Average of all",
                male_label: "Male",
                female_label: "Female",
                age_suffix: " yrs old"
            }
        };

        const postTypeLabels = {
            vi: {
                'Video': 'Video',
                'video': 'Video',
                'Photo': 'Hình ảnh',
                'Ảnh': 'Hình ảnh',
                'ảnh': 'Hình ảnh',
                'Shared link': 'Liên kết',
                'Liên kết chia sẻ': 'Liên kết',
                'liên kết chia sẻ': 'Liên kết',
                'Status update': 'Trạng thái',
                'Cập nhật trạng thái': 'Trạng thái',
                'cập nhật trạng thái': 'Trạng thái',
                'Unknown': 'Khác'
            },
            en: {
                'Video': 'Video',
                'video': 'Video',
                'Photo': 'Photo',
                'Ảnh': 'Photo',
                'ảnh': 'Photo',
                'Shared link': 'Link',
                'Liên kết chia sẻ': 'Link',
                'liên kết chia sẻ': 'Link',
                'Status update': 'Status',
                'Cập nhật trạng thái': 'Status',
                'cập nhật trạng thái': 'Status',
                'Unknown': 'Other'
            }
        };

        // Switch languages and translate UI
        function setLanguage(lang) {
            currentLang = lang;
            
            // Translate static elements with [data-i18n]
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (i18n[lang][key]) {
                    el.innerHTML = i18n[lang][key];
                }
            });
            
            // Update placeholders
            document.getElementById('table-search').placeholder = i18n[lang].table_search;
            
            // Update comparison dropdown placeholder
            const secondarySelect = document.getElementById('video-select-secondary');
            if (secondarySelect && secondarySelect.options[0]) {
                secondarySelect.options[0].textContent = i18n[lang].chart_compare;
            }
            
            // Adjust switch dot position (VI -> left, EN -> right)
            const dot = document.getElementById('lang-dot');
            const labelVi = document.getElementById('lang-label-vi');
            const labelEn = document.getElementById('lang-label-en');
            
            if (lang === 'en') {
                dot.style.transform = 'translateX(20px)';
                labelEn.style.color = '#818cf8';
                labelEn.style.fontWeight = '700';
                labelVi.style.color = '#9ca3af';
                labelVi.style.fontWeight = '500';
            } else {
                dot.style.transform = 'translateX(4px)';
                labelVi.style.color = '#818cf8';
                labelVi.style.fontWeight = '700';
                labelEn.style.color = '#9ca3af';
                labelEn.style.fontWeight = '500';
            }
            
            // Refresh variables
            updateAudienceHighlight();
            updateRetentionChart();
            renderAudienceChart();
            renderTable();
        }

        function toggleLanguage() {
            setLanguage(currentLang === 'vi' ? 'en' : 'vi');
        }

        // Format large numbers with dots (e.g. 1.234)
        function fmt(num) {
            return num.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, ".");
        }

        // Initialize KPIs
        document.getElementById('kpi-total-views').textContent = fmt(db.summary.total_views);
        document.getElementById('kpi-avg-duration').textContent = db.summary.avg_duration;
        document.getElementById('kpi-total-engagement').textContent = fmt(db.summary.total_engagement);
        
        const engRate = db.summary.total_views > 0 ? (db.summary.total_engagement / db.summary.total_views * 100).toFixed(1) : 0;
        document.getElementById('kpi-engagement-rate').textContent = engRate + '%';
        
        document.getElementById('kpi-ret-50').textContent = db.summary.top_ret_50_val + '%';
        document.getElementById('kpi-ret-50-title').textContent = db.summary.top_ret_50;
        document.getElementById('kpi-ret-50-title').setAttribute('title', db.summary.top_ret_50);
        
        document.getElementById('kpi-ret-100').textContent = db.summary.top_ret_100_val + '%';
        document.getElementById('kpi-ret-100-title').textContent = db.summary.top_ret_100;
        document.getElementById('kpi-ret-100-title').setAttribute('title', db.summary.top_ret_100);

        // Find top demographic
        let topDemoKey = "";
        let topDemoVal = -1;
        for (let k in db.demo_totals) {
            if (db.demo_totals[k] > topDemoVal) {
                topDemoVal = db.demo_totals[k];
                topDemoKey = k;
            }
        }
        
        function updateAudienceHighlight() {
            const demoGender = topDemoKey.split('_')[0] === 'M' ? i18n[currentLang].gender_male : i18n[currentLang].gender_female;
            const demoAge = topDemoKey.replace('M_', '').replace('F_', '').replace('_plus', '+').replace('_', '-');
            const suffix = i18n[currentLang].age_suffix;
            document.getElementById('audience-top-value').textContent = `${demoGender}, ${demoAge}${suffix}`;
        }

        // Render Video dropdowns (Only for posts with retention curves)
        const primarySelect = document.getElementById('video-select-primary');
        const secondarySelect = document.getElementById('video-select-secondary');
        
        const postsWithRet = db.posts.filter(p => p.has_retention);
        
        // Re-generate to map dynamic changes or updates
        function rebuildDropdowns() {
            primarySelect.innerHTML = '';
            secondarySelect.innerHTML = '';
            
            const compareOpt = document.createElement('option');
            compareOpt.value = "";
            compareOpt.textContent = i18n[currentLang].chart_compare;
            secondarySelect.appendChild(compareOpt);

            postsWithRet.forEach((p) => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = `${p.title.slice(0, 35)}${p.title.length > 35 ? '...' : ''} (${fmt(p.views)} views)`;
                primarySelect.appendChild(opt);
                
                const opt2 = opt.cloneNode(true);
                secondarySelect.appendChild(opt2);
            });
        }
        
        rebuildDropdowns();

        // Initialize Retention Chart
        let retChart = null;
        function updateRetentionChart() {
            const primaryId = primarySelect.value;
            const secondaryId = secondarySelect.value;
            
            const primaryPost = db.posts.find(p => p.id === primaryId);
            const secondaryPost = db.posts.find(p => p.id === secondaryId);
            
            const labels = Array.from({length: 41}, (_, i) => `Q${i}`);
            
            const datasets = [];
            
            // Average curve line
            datasets.push({
                label: i18n[currentLang].chart_avg_label,
                data: db.avg_ret_curve,
                borderColor: 'rgba(156, 163, 175, 0.4)',
                borderWidth: 2.5,
                borderDash: [6, 4],
                fill: false,
                pointRadius: 0
            });
            
            if (primaryPost && primaryPost.has_retention) {
                const dataPct = primaryPost.ret_total.map(v => v * 100);
                datasets.push({
                    label: primaryPost.title.slice(0, 25) + '...',
                    data: dataPct,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.07)',
                    borderWidth: 4,
                    fill: true,
                    pointRadius: 2.5,
                    pointHoverRadius: 7,
                    tension: 0.15
                });
            }
            
            if (secondaryPost && secondaryPost.has_retention) {
                const dataPct2 = secondaryPost.ret_total.map(v => v * 100);
                datasets.push({
                    label: secondaryPost.title.slice(0, 25) + '...',
                    data: dataPct2,
                    borderColor: '#ec4899',
                    backgroundColor: 'rgba(236, 72, 153, 0.03)',
                    borderWidth: 3.5,
                    fill: true,
                    pointRadius: 2.5,
                    pointHoverRadius: 7,
                    tension: 0.15
                });
            }
            
            const ctx = document.getElementById('retentionChart').getContext('2d');
            if (retChart) {
                retChart.destroy();
            }
            
            // Prevent crashes if canvas or context fails
            if (ctx) {
                retChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                min: 0,
                                max: 100,
                                ticks: {
                                    color: '#d1d5db',
                                    font: { weight: 'bold', family: 'Inter' },
                                    callback: function(value) { return value + '%'; }
                                },
                                grid: {
                                    color: 'rgba(75, 85, 99, 0.25)'
                                }
                            },
                            x: {
                                ticks: {
                                    color: '#d1d5db',
                                    font: { weight: 'bold', family: 'Inter' },
                                    maxTicksLimit: 11
                                },
                                grid: {
                                    display: false
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                labels: {
                                    color: '#ffffff',
                                    font: { weight: 'bold', family: 'Inter', size: 12 },
                                    boxWidth: 16
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return context.dataset.label + ': ' + context.raw.toFixed(1) + '%';
                                    }
                                }
                            }
                        }
                    }
                });
            }
        }
        
        primarySelect.addEventListener('change', updateRetentionChart);
        secondarySelect.addEventListener('change', updateRetentionChart);

        // Audience Demographics & Geography Charts
        let audienceChart = null;
        let activeAudienceTab = 'demo'; // 'demo' or 'geo'
        
        function renderAudienceChart() {
            const ctx = document.getElementById('audienceChart').getContext('2d');
            if (audienceChart) {
                audienceChart.destroy();
            }
            
            if (!ctx) return;
            
            if (activeAudienceTab === 'demo') {
                const labels = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"];
                const fData = [
                    db.demo_totals.F_18_24,
                    db.demo_totals.F_25_34,
                    db.demo_totals.F_35_44,
                    db.demo_totals.F_45_54,
                    db.demo_totals.F_55_64,
                    0
                ];
                const mData = [
                    db.demo_totals.M_18_24,
                    db.demo_totals.M_25_34,
                    db.demo_totals.M_35_44,
                    db.demo_totals.M_45_54,
                    db.demo_totals.M_55_64,
                    db.demo_totals.M_65_plus
                ];
                
                audienceChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: i18n[currentLang].gender_female,
                                data: fData,
                                backgroundColor: 'rgba(244, 114, 182, 0.9)',
                                borderRadius: 4
                            },
                            {
                                label: i18n[currentLang].gender_male,
                                data: mData,
                                backgroundColor: 'rgba(129, 140, 248, 0.9)',
                                borderRadius: 4
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'y',
                        scales: {
                            x: {
                                stacked: true,
                                ticks: { color: '#d1d5db', font: { weight: 'bold', family: 'Inter' } },
                                grid: { color: 'rgba(75, 85, 99, 0.25)' }
                            },
                            y: {
                                stacked: true,
                                ticks: { color: '#d1d5db', font: { weight: 'bold', family: 'Inter' } },
                                grid: { display: false }
                            }
                        },
                        plugins: {
                            legend: {
                                labels: { color: '#ffffff', font: { weight: 'bold', family: 'Inter' } }
                            }
                        }
                    }
                });
            } else {
                // Geo Chart
                const sortedGeo = Object.entries(db.country_totals)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 6);
                
                const labels = sortedGeo.map(x => x[0].split(' (')[0]);
                const data = sortedGeo.map(x => x[1]);
                
                audienceChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: [
                                '#818cf8',
                                '#a78bfa',
                                '#f472b6',
                                '#fbbf24',
                                '#34d399',
                                '#f87171'
                            ],
                            borderWidth: 1.5,
                            borderColor: '#0b0f19'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right',
                                labels: {
                                    color: '#ffffff',
                                    font: { weight: 'bold', family: 'Inter' },
                                    boxWidth: 12
                                }
                            }
                        }
                    }
                });
            }
        }
        
        document.getElementById('tab-demo-btn').addEventListener('click', (e) => {
            activeAudienceTab = 'demo';
            e.target.className = "px-3 py-1.5 text-xs font-bold bg-indigo-600 text-white rounded-lg transition-colors";
            document.getElementById('tab-geo-btn').className = "px-3 py-1.5 text-xs font-bold bg-gray-800 text-gray-300 hover:bg-gray-700 rounded-lg transition-colors";
            renderAudienceChart();
        });
        
        document.getElementById('tab-geo-btn').addEventListener('click', (e) => {
            activeAudienceTab = 'geo';
            e.target.className = "px-3 py-1.5 text-xs font-bold bg-indigo-600 text-white rounded-lg transition-colors";
            document.getElementById('tab-demo-btn').className = "px-3 py-1.5 text-xs font-bold bg-gray-800 text-gray-300 hover:bg-gray-700 rounded-lg transition-colors";
            renderAudienceChart();
        });

        // Search & Sorting of Table
        let currentSort = 'views'; // 'views' or 'ret'
        const tableSearch = document.getElementById('table-search');
        
        function renderTable() {
            const query = tableSearch.value.toLowerCase().trim();
            const tbody = document.getElementById('video-table-body');
            tbody.innerHTML = '';
            
            let filtered = db.posts.filter(p => 
                p.title.toLowerCase().includes(query) || 
                p.description.toLowerCase().includes(query)
            );
            
            if (currentSort === 'views') {
                filtered.sort((a, b) => b.views - a.views);
            } else {
                filtered.sort((a, b) => b.ret_checkpoints.p50 - a.ret_checkpoints.p50);
            }
            
            filtered.forEach(p => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-gray-800/40 transition-colors border-b border-gray-800/50";
                
                const formattedViews = fmt(p.views);
                const formattedEngagement = fmt(p.engagement);
                
                const isVideo = p.post_type === 'Video';
                const durationText = isVideo ? `${Math.floor(p.duration / 60)}m ${Math.round(p.duration % 60)}s` : '<span class="text-gray-500 font-bold">-</span>';
                
                const ret25 = (p.has_retention && isVideo) ? p.ret_checkpoints.p25.toFixed(1) + '%' : '<span class="text-gray-500 font-bold">-</span>';
                const ret50 = (p.has_retention && isVideo) ? p.ret_checkpoints.p50.toFixed(1) + '%' : '<span class="text-gray-500 font-bold">-</span>';
                const ret100 = (p.has_retention && isVideo) ? p.ret_checkpoints.p100.toFixed(1) + '%' : '<span class="text-gray-500 font-bold">-</span>';
                
                // Construct beautiful badge for post type
                let badgeClass = "bg-gray-800/80 text-gray-300 border border-gray-700";
                if (p.post_type === 'Video') {
                    badgeClass = "bg-indigo-500/15 text-indigo-300 border border-indigo-500/25";
                } else if (p.post_type === 'Photo' || p.post_type === 'Ảnh') {
                    badgeClass = "bg-emerald-500/15 text-emerald-300 border border-emerald-500/25";
                } else if (p.post_type === 'Shared link' || p.post_type === 'Liên kết chia sẻ') {
                    badgeClass = "bg-amber-500/15 text-amber-300 border border-amber-500/25";
                }
                
                const typeLabel = postTypeLabels[currentLang][p.post_type] || p.post_type;
                const typeBadge = `<span class="px-2 py-0.5 text-[10px] font-bold rounded ${badgeClass} mr-2 shadow-sm">${typeLabel}</span>`;
                
                tr.innerHTML = `
                    <td class="py-4 px-4 font-bold text-white max-w-[280px] truncate" title="${p.title}">
                        <div class="flex items-center" style="display:flex; align-items:center;">
                            ${typeBadge}
                            <span class="truncate text-[13px] md:text-sm font-semibold">${p.title}</span>
                        </div>
                    </td>
                    <td class="py-4 px-3 text-center text-gray-300 font-semibold text-[13px] md:text-sm">
                        ${durationText}
                    </td>
                    <td class="py-4 px-3 text-right font-bold text-white text-[13px] md:text-sm">
                        ${formattedViews}
                    </td>
                    <td class="py-4 px-3 text-right text-gray-300 font-semibold text-[13px] md:text-sm">
                        ${formattedEngagement}
                    </td>
                    <td class="py-4 px-3 text-right font-extrabold text-indigo-300 text-[13px] md:text-sm">
                        ${ret25}
                    </td>
                    <td class="py-4 px-3 text-right font-extrabold text-purple-300 text-[13px] md:text-sm">
                        ${ret50}
                    </td>
                    <td class="py-4 px-3 text-right font-extrabold text-emerald-300 text-[13px] md:text-sm">
                        ${ret100}
                    </td>
                    <td class="py-4 px-4 text-center">
                        <a href="${p.permalink}" target="_blank" class="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/25 rounded hover:bg-indigo-500 hover:text-white transition-colors duration-200 shadow-sm">
                            ${i18n[currentLang].btn_details}
                        </a>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            
            const totalCount = db.posts.length;
            const shownCount = filtered.length;
            let metaText = i18n[currentLang].table_meta;
            metaText = metaText.replace('{shown}', shownCount).replace('{total}', totalCount);
            document.getElementById('table-meta').textContent = metaText;
        }
        
        tableSearch.addEventListener('input', renderTable);
        
        document.getElementById('sort-views-btn').addEventListener('click', (e) => {
            currentSort = 'views';
            e.target.className = "px-3.5 py-2.5 text-xs font-bold bg-indigo-600 text-white rounded-lg transition-colors";
            document.getElementById('sort-ret-btn').className = "px-3.5 py-2.5 text-xs font-bold bg-gray-800 text-gray-300 hover:bg-gray-700 rounded-lg transition-colors";
            renderTable();
        });
        
        document.getElementById('sort-ret-btn').addEventListener('click', (e) => {
            currentSort = 'ret';
            e.target.className = "px-3.5 py-2.5 text-xs font-bold bg-indigo-600 text-white rounded-lg transition-colors";
            document.getElementById('sort-views-btn').className = "px-3.5 py-2.5 text-xs font-bold bg-gray-800 text-gray-300 hover:bg-gray-700 rounded-lg transition-colors";
            renderTable();
        });

        // Bootstrap
        setLanguage('vi');
    </script>
</body>
</html>
"""
    
    # Replace pre-rendered template fields
    html_content = html_template.replace('{TOTAL_VIEWS_FMT}', total_views_fmt)
    html_content = html_content.replace('{AVG_DURATION_FMT}', avg_duration_fmt)
    html_content = html_content.replace('{TOTAL_ENGAGEMENT_FMT}', total_engagement_fmt)
    html_content = html_content.replace('{ENG_RATE_FMT}', eng_rate_fmt)
    html_content = html_content.replace('{TOP_RET_50_VAL_FMT}', top_ret_50_val_fmt)
    html_content = html_content.replace('{TOP_RET_50_TITLE}', top_ret_50_title)
    html_content = html_content.replace('{TOP_RET_100_VAL_FMT}', top_ret_100_val_fmt)
    html_content = html_content.replace('{TOP_RET_100_TITLE}', top_ret_100_title)
    html_content = html_content.replace('{TABLE_ROWS_HTML}', table_rows_html)
    html_content = html_content.replace('{PRIMARY_OPTIONS_HTML}', primary_options_html)
    html_content = html_content.replace('{SECONDARY_OPTIONS_HTML}', secondary_options_html)
    html_content = html_content.replace('{TOTAL_POSTS}', str(len(posts)))
    
    # Inject actual JSON DB
    html_content = html_content.replace('__REPORT_DATA__', data_json)
    
    # Inject Fallback CSS elements
    html_content = html_content.replace('{FALLBACK_CHART_BARS}', fallback_chart_bars_html)
    html_content = html_content.replace('{FALLBACK_AUDIENCE_HTML}', fallback_audience_html)

    with open(HTML_OUTPUT, mode='w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Generated HTML Dashboard: {HTML_OUTPUT}")

def main():
    print("Starting Facebook Video Retention Report generation...")
    print(f"Reading data file: {CSV_PATH}")
    posts = parse_csv()
    print(f"Successfully parsed {len(posts)} videos.")
    
    if not posts:
        print("No videos found to process.")
        return
        
    generate_csv_summary(posts)
    generate_html_report(posts)
    print("Report generation complete!")

if __name__ == "__main__":
    main()
