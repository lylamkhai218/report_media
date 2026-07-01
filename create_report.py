import csv
import json
import os
import sys
import glob

# Ensure console can print utf-8 characters on Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# Tự động tìm kiếm các file CSV dữ liệu Facebook Insights theo tháng trong thư mục data/
REPORT_DIR = r"d:\T&TVina\Report"
DATA_DIR = os.path.join(REPORT_DIR, "data")
HTML_OUTPUT = os.path.join(REPORT_DIR, "report_media.html")
CSV_OUTPUT = os.path.join(REPORT_DIR, "report_giu_chan_summary.csv")

def find_monthly_csvs():
    all_csvs = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    
    months_num_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    
    monthly_files = {}
    for fpath in all_csvs:
        if os.path.abspath(fpath) == os.path.abspath(CSV_OUTPUT):
            continue
        try:
            with open(fpath, mode='r', encoding='utf-8-sig', errors='ignore') as f:
                header = f.readline()
                if "ID bài viết" not in header and "Post ID" not in header:
                    continue
        except Exception:
            continue
            
        fname = os.path.basename(fpath)
        import re
        match = re.search(r"([A-Za-z]{3})-\d{2}-\d{4}_([A-Za-z]{3})-\d{2}-\d{4}", fname)
        if match:
            start_str, end_str = match.groups()
            start_m = months_num_map.get(start_str.lower())
            end_m = months_num_map.get(end_str.lower())
            # Chỉ nhận các file có cùng tháng bắt đầu và kết thúc (file báo cáo tháng thực sự)
            if start_m and end_m and start_m == end_m:
                m_idx = end_m
                mtime = os.path.getmtime(fpath)
                size = os.path.getsize(fpath)
                if m_idx not in monthly_files:
                    monthly_files[m_idx] = []
                monthly_files[m_idx].append((fpath, mtime, size, fname))
                
    selected_files = {}
    for m_idx, files_list in monthly_files.items():
        # Sắp xếp theo thời gian chỉnh sửa mới nhất
        files_list.sort(key=lambda x: x[1], reverse=True)
        selected_files[m_idx] = files_list[0][0]
        
    return selected_files

MONTHLY_CSVS = find_monthly_csvs()

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

def parse_csv(csv_path):
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return []

    def find_column_indices(headers):
        indices = {}
        def get_index(keywords, exact=False):
            for idx, h in enumerate(headers):
                h_clean = h.strip()
                if exact:
                    if any(h_clean == kw for kw in keywords):
                        return idx
                else:
                    if any(kw.lower() in h_clean.lower() for kw in keywords):
                        return idx
            return -1

        indices['post_id'] = get_index(["ID bài viết", "Post ID", "ID"], exact=True)
        if indices['post_id'] == -1:
            indices['post_id'] = get_index(["ID bài viết", "Post ID", "ID"])
        indices['page_name'] = get_index(["Tên Trang", "Page name"])
        indices['title'] = get_index(["Tiêu đề", "Title"], exact=True)
        if indices['title'] == -1:
            indices['title'] = get_index(["Tiêu đề", "Title"])
        indices['description'] = get_index(["Mô tả", "Description"])
        indices['duration'] = get_index(["Thời lượng (giây)", "Duration (seconds)", "Thời lượng", "Duration"])
        indices['publish_date'] = get_index(["Thời gian đăng", "Publish time", "Published"])
        indices['permalink'] = get_index(["Liên kết vĩnh viễn", "Permalink", "Link"])
        indices['post_type'] = get_index(["Loại bài viết", "Post type"])
        indices['views'] = get_index(["Lượt xem", "Views"], exact=True)
        indices['reach'] = get_index(["Số người tiếp cận", "Reach"])
        indices['engagement'] = get_index(["Cảm xúc, bình luận và lượt chia sẻ", "Engagement"])
        indices['likes'] = get_index(["Cảm xúc", "Likes"], exact=True)
        indices['comments'] = get_index(["Bình luận", "Comments"], exact=True)
        indices['shares'] = get_index(["Lượt chia sẻ", "Shares"], exact=True)
        indices['clicks'] = get_index(["Tổng lượt click", "Clicks"], exact=True)
        indices['organic_views'] = get_index(["Lượt xem từ Bài viết tự nhiên", "Organic views"])
        indices['paid_views'] = get_index(["Lượt xem từ Bài viết đã quảng cáo", "Paid views"])
        indices['ret_total_start'] = get_index(["Phần trăm tổng số lượt xem ở quãng 0", "Percentage of total views at checkpoint 0"])
        indices['ret_15s_start'] = get_index(["Phần trăm số lượt xem trong tối thiểu 15 giây ở quãng 0", "Percentage of views for at least 15 seconds at checkpoint 0"])
        return indices

    posts = []
    
    with open(csv_path, mode='r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.reader(f)
        headers = next(reader)
        
        indices = find_column_indices(headers)
        
        # Build demographic mappings
        demo_col_map = {}
        for idx, h in enumerate(headers):
            if "đối tượng hàng đầu" in h or "top audience" in h:
                import re
                m = re.search(r"\((M|F),\s*(\d+-\d+|\d+\+)\)", h)
                if m:
                    gender, age = m.groups()
                    age_key = age.replace('+', '_plus').replace('-', '_')
                    key = f"{gender}_{age_key}"
                    demo_col_map[key] = idx
                    
        # Build country mappings - using greedy match to support nested parentheses
        country_col_map = {}
        for idx, h in enumerate(headers):
            if "theo quốc gia" in h or "by country" in h:
                import re
                m = re.search(r"\((.*)\)\s*$", h)
                if m:
                    country_name = m.group(1)
                    country_col_map[country_name] = idx
                    
        def get_val(row, field, default=""):
            idx = indices.get(field, -1)
            if idx != -1 and idx < len(row):
                return row[idx].strip()
            return default

        def get_float(row, field, default=0.0):
            return safe_float(get_val(row, field), default)

        def get_int(row, field, default=0):
            return safe_int(get_val(row, field), default)
        
        for row in reader:
            if not row:
                continue
                
            post_id = get_val(row, 'post_id')
            if not post_id or post_id in ("ID bài viết", "Post ID", "ID"):
                continue
                
            post_type = get_val(row, 'post_type') or "Unknown"
            duration = get_float(row, 'duration')
            views = get_int(row, 'views')
            page_name = get_val(row, 'page_name')
            title = get_val(row, 'title')
            description = get_val(row, 'description')
            
            if not title:
                clean_desc = description.replace('\n', ' ').strip()
                title = clean_desc[:50] + "..." if len(clean_desc) > 50 else (clean_desc or f"{post_type} {post_id}")
            
            publish_date = get_val(row, 'publish_date')
            permalink = get_val(row, 'permalink')
            reach = get_int(row, 'reach')
            engagement = get_int(row, 'engagement')
            likes = get_int(row, 'likes')
            comments = get_int(row, 'comments')
            shares = get_int(row, 'shares')
            clicks = get_int(row, 'clicks')
            organic_views = get_int(row, 'organic_views')
            paid_views = get_int(row, 'paid_views')
            
            # Parse retention curves
            ret_total = []
            start_idx = indices.get('ret_total_start', -1)
            if start_idx != -1:
                for i in range(start_idx, start_idx + 41):
                    ret_total.append(safe_float(row[i]) if i < len(row) else 0.0)
            else:
                ret_total = [0.0] * 41
                
            ret_15s = []
            start_idx = indices.get('ret_15s_start', -1)
            if start_idx != -1:
                for i in range(start_idx, start_idx + 41):
                    ret_15s.append(safe_float(row[i]) if i < len(row) else 0.0)
            else:
                ret_15s = [0.0] * 41
            
            # Demographics
            demographics = {}
            for demo_key, idx in demo_col_map.items():
                demographics[demo_key] = safe_int(row[idx]) if idx < len(row) else 0
            all_demo_keys = [
                "M_18_24", "M_25_34", "M_35_44", "M_45_54", "M_55_64", "M_65_plus",
                "F_18_24", "F_25_34", "F_35_44", "F_45_54", "F_55_64"
            ]
            for dk in all_demo_keys:
                if dk not in demographics:
                    demographics[dk] = 0
            
            # Countries
            countries = {}
            for country_name, idx in country_col_map.items():
                countries[country_name] = safe_int(row[idx]) if idx < len(row) else 0
            standard_countries = ["Vietnam (VN)", "Japan (JP)", "Pakistan (PK)", "Germany (DE)", "India (IN)", "Indonesia (ID)"]
            for c in standard_countries:
                if c not in countries:
                    countries[c] = 0
            
            has_retention = any(v > 0 for v in ret_total) and (post_type == "Video" or duration > 0)
            
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

def generate_csv_summary(monthly_posts):
    # Kết hợp toàn bộ bài viết và bổ sung cột Tháng
    all_posts = []
    for m_idx, posts in monthly_posts.items():
        for p in posts:
            p_copy = p.copy()
            p_copy['month'] = f"Tháng {m_idx}"
            all_posts.append(p_copy)
            
    # Sắp xếp bài viết theo lượt xem giảm dần
    sorted_posts = sorted(all_posts, key=lambda x: x['views'], reverse=True)
    
    with open(CSV_OUTPUT, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Tháng", "ID Bài Viết", "Tiêu Đề", "Loại Bài Viết", "Thời Lượng (s)", "Ngày Đăng", 
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
                p['month'], p['id'], p['title'], p['post_type'], p['duration'] if p['post_type'] == "Video" else "-", p['publish_date'],
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

def generate_html_report(monthly_posts):
    import re
    
    months_map_vi = {
        "jan": "tháng 1", "feb": "tháng 2", "mar": "tháng 3", "apr": "tháng 4", "may": "tháng 5", "jun": "tháng 6",
        "jul": "tháng 7", "aug": "tháng 8", "sep": "tháng 9", "oct": "tháng 10", "nov": "tháng 11", "dec": "tháng 12"
    }
    months_map_en = {
        "jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr", "may": "May", "jun": "Jun",
        "jul": "Jul", "aug": "Aug", "sep": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec"
    }
    months_num_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }

    report_subtitle_vi = "Murrplastik Việt Nam · Báo cáo tháng"
    report_subtitle_en = "Murrplastik Vietnam · Monthly Report"

    # Tính toán số liệu cho từng tháng
    report_data_all = {}
    
    for m_idx, posts in monthly_posts.items():
        # Lấy ngày cập nhật từ file CSV
        csv_path = MONTHLY_CSVS[m_idx]
        filename = os.path.basename(csv_path)
        report_date = f"30/{m_idx:02d}/2026"
        
        match = re.search(r"([A-Za-z]{3}-\d{2}-\d{4})_([A-Za-z]{3}-\d{2}-\d{4})", filename)
        if match:
            start_str, end_str = match.groups()
            parts_start = start_str.split('-')
            parts_end = end_str.split('-')
            if len(parts_start) == 3 and len(parts_end) == 3:
                s_m, s_d, s_y = parts_start
                e_m, e_d, e_y = parts_end
                s_m_idx = months_num_map.get(s_m.lower(), m_idx)
                e_m_idx = months_num_map.get(e_m.lower(), m_idx)
                report_date = f"{e_d}/{e_m_idx:02d}/{e_y}"

        total_views = sum(p['views'] for p in posts)
        total_reach = sum(p['reach'] for p in posts)
        total_engagement = sum(p['engagement'] for p in posts)
        
        video_posts = [p for p in posts if p['post_type'] == "Video" or p['duration'] > 0]
        total_duration = sum(p['duration'] for p in video_posts)
        avg_duration = total_duration / len(video_posts) if video_posts else 0.0
        
        sorted_by_views = sorted(posts, key=lambda x: x['views'], reverse=True)
        top_viewed = sorted_by_views[0] if sorted_by_views else None
        
        posts_with_ret = [p for p in posts if p['has_retention']]
        top_ret_50 = sorted(posts_with_ret, key=lambda x: x['ret_checkpoints']['p50'], reverse=True)[0] if posts_with_ret else None
        top_ret_100 = sorted(posts_with_ret, key=lambda x: x['ret_checkpoints']['p100'], reverse=True)[0] if posts_with_ret else None
        
        demo_totals = {
            "M_18_24": 0, "M_25_34": 0, "M_35_44": 0, "M_45_54": 0, "M_55_64": 0, "M_65_plus": 0,
            "F_18_24": 0, "F_25_34": 0, "F_35_44": 0, "F_45_54": 0, "F_55_64": 0
        }
        country_totals = {
            "Vietnam (VN)": 0, "Japan (JP)": 0, "Pakistan (PK)": 0, "Germany (DE)": 0, "India (IN)": 0, "Indonesia (ID)": 0
        }
        
        for p in posts:
            for k, v in p['demographics'].items():
                if k in demo_totals:
                    demo_totals[k] += v
            for k, v in p['countries'].items():
                if k in country_totals:
                    country_totals[k] += v
                    
        avg_ret_curve = [0.0] * 41
        if posts_with_ret:
            for i in range(41):
                avg_ret_curve[i] = sum(p['ret_total'][i] for p in posts_with_ret) / len(posts_with_ret) * 100
                
        report_data_all[str(m_idx)] = {
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
            "avg_ret_curve": avg_ret_curve,
            "report_date": report_date
        }

    # Chọn tháng mới nhất làm mặc định hiển thị
    latest_month = max(monthly_posts.keys())
    latest_data = report_data_all[str(latest_month)]
    latest_posts = latest_data["posts"]
    latest_summary = latest_data["summary"]
    latest_demo_totals = latest_data["demo_totals"]
    latest_country_totals = latest_data["country_totals"]
    latest_avg_ret_curve = latest_data["avg_ret_curve"]
    latest_report_date = latest_data["report_date"]
    
    total_views_fmt = f"{latest_summary['total_views']:,}".replace(",", ".")
    total_engagement_fmt = f"{latest_summary['total_engagement']:,}".replace(",", ".")
    avg_duration_fmt = f"{latest_summary['avg_duration']:.1f}"
    
    eng_rate = (latest_summary['total_engagement'] / latest_summary['total_views'] * 100) if latest_summary['total_views'] > 0 else 0.0
    eng_rate_fmt = f"{eng_rate:.1f}"
    
    top_ret_50_val_fmt = f"{latest_summary['top_ret_50_val']:.1f}%" if latest_summary['top_ret_50_val'] > 0 else "-"
    top_ret_50_title = latest_summary['top_ret_50']
    
    top_ret_100_val_fmt = f"{latest_summary['top_ret_100_val']:.1f}%" if latest_summary['top_ret_100_val'] > 0 else "-"
    top_ret_100_title = latest_summary['top_ret_100']
    
    # Render trước bảng xếp hạng bằng Python (dữ liệu tháng mới nhất)
    table_rows_html = ""
    sorted_by_views = sorted(latest_posts, key=lambda x: x['views'], reverse=True)
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
        
    posts_with_ret = [p for p in latest_posts if p['has_retention']]
    primary_options_html = ""
    secondary_options_html = f'<option value="" data-i18n="chart_compare">-- So sánh với... --</option>\n'
    for p in posts_with_ret:
        title_trunc = p['title'][:35] + "..." if len(p['title']) > 35 else p['title']
        views_opt = f"{p['views']:,}".replace(",", ".")
        primary_options_html += f'<option value="{p["id"]}">{title_trunc} ({views_opt} views)</option>\n'
        secondary_options_html += f'<option value="{p["id"]}">{title_trunc} ({views_opt} views)</option>\n'

    # Fallback chart bars (đường cong trung bình tháng mới nhất)
    fallback_chart_bars_html = ""
    primary_post = posts_with_ret[0] if posts_with_ret else None
    if primary_post:
        ret_data = primary_post['ret_total']
        for i in range(0, 41, 2):
            val = ret_data[i] * 100
            lbl = f"{int(i * 2.5)}%" if i % 8 == 0 else ""
            fallback_chart_bars_html += f"""
            <div class="fallback-bar-wrapper" style="display:flex; flex-direction:column; align-items:center; flex:1; height:100%; justify-content:flex-end; position:relative;">
                <div class="fallback-bar" style="height: {val:.0f}%; width: 55%; background: linear-gradient(180deg, #6366f1 0%, rgba(99,102,241,0.2) 100%); border-radius: 2px 2px 0 0;"></div>
                <span style="font-size: 8px; color: #6b7280; margin-top: 4px; height: 12px;">{lbl}</span>
            </div>
            """

    # Fallback audience HTML
    fallback_audience_html = ""
    sorted_demo = sorted(latest_demo_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    max_demo_val = max(latest_demo_totals.values()) if latest_demo_totals.values() else 1
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
            
    # Chuẩn bị dữ liệu JSON lưu trữ toàn bộ các tháng
    data_json = json.dumps(report_data_all, ensure_ascii=False)
    
    html_template = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>MEDIA PERFORMANCE ANALYSIS - Murrplastik VN</title>
    <!-- Open Graph / Facebook / Zalo Link Preview -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://lylamkhai218.github.io/report_media/report_media.html">
    <meta property="og:title" content="MEDIA PERFORMANCE ANALYSIS - Murrplastik VN">
    <meta property="og:description" content="Báo cáo phân tích hiệu suất truyền thông và tỷ lệ giữ chân video của Murrplastik Việt Nam.">
    <meta property="og:image" content="https://lylamkhai218.github.io/report_media/assets/preview.png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">

    <!-- Favicon -->
    <link rel="icon" type="image/png" href="favicon.png">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect x='4' y='18' width='6' height='10' rx='1.5' fill='%23e3001b'/%3E%3Crect x='13' y='10' width='6' height='18' rx='1.5' fill='%23e3001b'/%3E%3Crect x='22' y='2' width='6' height='26' rx='1.5' fill='%23e3001b'/%3E%3C/svg%3E">
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Google Fonts Inter (High legibility for screen sharing) -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* CSS Theme Variables */
        :root {
            /* Light theme (default) */
            --bg-color: #f8fafc;
            --text-color: #0f172a;
            --header-bg: #ffffff;
            --header-border: #e2e8f0;
            --card-bg: rgba(255, 255, 255, 0.85);
            --card-border: rgba(148, 163, 184, 0.18);
            --card-shadow: 0 10px 15px -3px rgba(148, 163, 184, 0.08), 0 4px 6px -4px rgba(148, 163, 184, 0.08);
            --card-hover-shadow: 0 20px 25px -5px rgba(99, 102, 241, 0.12), 0 8px 10px -6px rgba(99, 102, 241, 0.12);
            --select-bg: #ffffff;
            --select-color: #0f172a;
            --select-border: #cbd5e1;
            --table-container-bg: rgba(255, 255, 255, 0.5);
            --table-container-border: #cbd5e1;
            --th-bg: #f1f5f9;
            --th-color: #475569;
            --th-border: #cbd5e1;
            --td-border: rgba(148, 163, 184, 0.12);
            --text-muted: #475569;
            --sticky-th-shadow: 0 2px 8px rgba(148, 163, 184, 0.12);
            --warning-bg: rgba(239, 68, 68, 0.06);
            --warning-border: rgba(239, 68, 68, 0.18);
            --warning-text: #dc2626;
            --tr-hover: rgba(226, 232, 240, 0.5);
            --glass-panel-bg: rgba(255, 255, 255, 0.7);
            --glass-panel-border: rgba(148, 163, 184, 0.18);
            --table-body-bg: rgba(255, 255, 255, 0.35);
            --divider: #cbd5e1;
            --scrollbar-thumb: rgba(0, 0, 0, 0.15);
            --scrollbar-thumb-hover: rgba(0, 0, 0, 0.25);
            --tab-active-bg: #4f46e5;
            --tab-active-text: #ffffff;
            --tab-inactive-bg: transparent;
            --tab-inactive-text: #475569;
            --tab-hover-bg: rgba(226, 232, 240, 0.8);
            --tab-hover-text: #0f172a;
            --tab-active-shadow: 0 0 10px rgba(79, 70, 229, 0.2);
        }

        :root.dark {
            /* Dark theme */
            --bg-color: #080c14;
            --text-color: #ffffff;
            --header-bg: #0d1321;
            --header-border: #1f2937;
            --card-bg: rgba(19, 26, 42, 0.85);
            --card-border: rgba(255, 255, 255, 0.09);
            --card-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            --card-hover-shadow: 0 0 25px rgba(99,102,241,0.15);
            --select-bg: #1f2937;
            --select-color: #ffffff;
            --select-border: #374151;
            --table-container-bg: rgba(19, 26, 42, 0.5);
            --table-container-border: #1f2937;
            --th-bg: #0d1321;
            --th-color: #9ca3af;
            --th-border: rgba(255, 255, 255, 0.1);
            --td-border: rgba(255, 255, 255, 0.05);
            --text-muted: #9ca3af;
            --sticky-th-shadow: 0 2px 8px rgba(0, 0, 0, 0.6);
            --warning-bg: rgba(239, 68, 68, 0.15);
            --warning-border: rgba(239, 68, 68, 0.25);
            --warning-text: #f87171;
            --tr-hover: rgba(255, 255, 255, 0.04);
            --glass-panel-bg: rgba(13, 19, 33, 0.45);
            --glass-panel-border: rgba(255, 255, 255, 0.08);
            --table-body-bg: rgba(9, 13, 22, 0.3);
            --divider: #1f2937;
            --scrollbar-thumb: rgba(255, 255, 255, 0.2);
            --scrollbar-thumb-hover: rgba(255, 255, 255, 0.35);
            --tab-active-bg: #6366f1;
            --tab-active-text: #ffffff;
            --tab-inactive-bg: transparent;
            --tab-inactive-text: #9ca3af;
            --tab-hover-bg: rgba(255, 255, 255, 0.08);
            --tab-hover-text: #ffffff;
            --tab-active-shadow: 0 0 10px rgba(99, 102, 241, 0.4);
        }

        /* Force border-box model globally to prevent horizontal scroll stretching */
        *, *::before, *::after {
            box-sizing: border-box !important;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 0;
            letter-spacing: -0.011em;
            width: 100%;
            overflow-x: hidden; /* Avoid side scrolling */
            transition: background-color 0.3s ease, color 0.3s ease;
        }
        
        header {
            background-color: var(--header-bg);
            border-bottom: 1px solid var(--header-border);
            padding: 20px 16px;
            width: 100%;
            transition: background-color 0.3s ease, border-color 0.3s ease;
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
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 20px;
            box-shadow: var(--card-shadow);
            position: relative;
            min-width: 0; /* Keep items from pushing width */
            width: 100%;
            transition: background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
        }
        .card:hover {
            box-shadow: var(--card-hover-shadow);
        }

        .glass-panel {
            background: var(--glass-panel-bg) !important;
            border-color: var(--glass-panel-border) !important;
            transition: background-color 0.3s ease, border-color 0.3s ease;
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
            background-color: var(--select-bg);
            color: var(--select-color);
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid var(--select-border);
            font-size: 12px;
            max-width: 100%;
            width: 100%;
            text-overflow: ellipsis;
            white-space: nowrap;
            overflow: hidden;
            display: block;
            transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
        }
        
        .table-container {
            overflow-x: auto;
            overflow-y: auto;
            max-height: 70vh;
            border: 1px solid var(--table-container-border);
            border-radius: 12px;
            background-color: var(--table-container-bg);
            margin-top: 16px;
            width: 100%;
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }
        
        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            text-align: left;
        }
        
        th, td {
            padding: 14px 16px;
        }

        td {
            font-size: 14px;
            max-width: 280px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            border-bottom: 1px solid var(--td-border);
            transition: border-color 0.3s ease;
        }
        
        th {
            background-color: var(--th-bg);
            color: var(--th-color);
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 2px solid var(--th-border);
            transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
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
        
        /* Light Theme badge style overrides for better readability */
        :root:not(.dark) .badge-video { background-color: rgba(79, 70, 229, 0.1) !important; color: #4338ca !important; border: 1px solid rgba(79, 70, 229, 0.2) !important; }
        :root:not(.dark) .badge-photo { background-color: rgba(5, 150, 105, 0.1) !important; color: #047857 !important; border: 1px solid rgba(5, 150, 105, 0.2) !important; }
        :root:not(.dark) .badge-link { background-color: rgba(217, 119, 6, 0.1) !important; color: #b45309 !important; border: 1px solid rgba(217, 119, 6, 0.2) !important; }
        
        /* Premium variable-driven Month Switcher Tab Buttons */
        .month-tab-btn {
            background-color: var(--tab-inactive-bg) !important;
            color: var(--tab-inactive-text) !important;
            transition: all 0.2s ease-in-out;
        }
        .month-tab-btn:hover {
            background-color: var(--tab-hover-bg) !important;
            color: var(--tab-hover-text) !important;
        }
        .month-tab-btn.active {
            background-color: var(--tab-active-bg) !important;
            color: var(--tab-active-text) !important;
            box-shadow: var(--tab-active-shadow) !important;
        }
        
        .fallback-chart-container {
            display: flex;
            align-items: flex-end;
            gap: 4px;
            height: 250px;
            background: rgba(8, 12, 20, 0.03);
            border: 1px solid var(--td-border);
            padding: 16px 8px;
            border-radius: 8px;
            width: 100%;
        }

        :root.dark .fallback-chart-container {
            background: rgba(8, 12, 20, 0.5);
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
            background: rgba(0, 0, 0, 0.02);
        }
        :root.dark .custom-scrollbar::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.01);
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
            background: var(--scrollbar-thumb);
            border-radius: 99px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: var(--scrollbar-thumb-hover);
        }
        
        /* Sticky header row - sticky within scroll container */
        .sticky-th {
            position: sticky;
            top: 0;
            background-color: var(--th-bg);
            z-index: 20;
            box-shadow: var(--sticky-th-shadow);
        }
        @media (min-width: 768px) {
            .table-container {
                max-height: 75vh;
                overflow-y: auto;
                overflow-x: auto;
            }
            .sticky-th {
                position: sticky;
                top: 0;
                z-index: 10;
            }
        }

        #js-warning {
            background-color: var(--warning-bg) !important;
            border-color: var(--warning-border) !important;
            color: var(--warning-text) !important;
            transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
        }

        /* Override Tailwind text/bg colors for Light Theme */
        :root:not(.dark) .text-white { color: #0f172a !important; }
        :root:not(.dark) .text-gray-400 { color: #475569 !important; }
        :root:not(.dark) .text-gray-300 { color: #334155 !important; }
        :root:not(.dark) .text-gray-200 { color: #1e293b !important; }
        :root:not(.dark) .text-indigo-400 { color: #4f46e5 !important; }
        :root:not(.dark) .text-purple-400 { color: #7c3aed !important; }
        :root:not(.dark) .text-purple-300 { color: #6d28d9 !important; }
        :root:not(.dark) .text-indigo-300 { color: #4338ca !important; }
        :root:not(.dark) .text-emerald-300 { color: #047857 !important; }
        :root:not(.dark) .text-emerald-400 { color: #059669 !important; }
        
        /* Exception: keep white text inside dark backgrounds (like indigo buttons/tabs) */
        :root:not(.dark) .bg-indigo-600,
        :root:not(.dark) .bg-indigo-600 *,
        :root:not(.dark) .bg-indigo-500,
        :root:not(.dark) .bg-indigo-500 *,
        :root:not(.dark) button.bg-indigo-600,
        :root:not(.dark) button.bg-indigo-600 *,
        :root:not(.dark) a.hover\\:text-white:hover,
        :root:not(.dark) .hover\\:text-white:hover {
            color: #ffffff !important;
        }

        :root:not(.dark) .bg-gray-800 { background-color: #f1f5f9 !important; }
        :root:not(.dark) .bg-gray-800\\/40 { background-color: rgba(241, 245, 249, 0.4) !important; }
        :root:not(.dark) .bg-gray-900\\/60 { background-color: rgba(241, 245, 249, 0.6) !important; }
        :root:not(.dark) .bg-gray-900\\/80 { background-color: rgba(241, 245, 249, 0.8) !important; }
        :root:not(.dark) .bg-gray-950 { background-color: #f8fafc !important; }
        :root:not(.dark) .bg-\\[\\#0d1321\\] { background-color: #ffffff !important; }
        :root:not(.dark) .bg-\\[\\#090d16\\]\\/30 { background-color: rgba(241, 245, 249, 0.3) !important; }
        :root:not(.dark) .bg-gray-900\\/50 { background-color: rgba(226, 232, 240, 0.45) !important; }
        :root:not(.dark) .bg-gray-900\\/30 { background-color: rgba(226, 232, 240, 0.3) !important; }
        
        :root:not(.dark) .border-gray-800 { border-color: #cbd5e1 !important; }
        :root:not(.dark) .border-gray-800\\/50 { border-color: rgba(203, 213, 225, 0.5) !important; }
        :root:not(.dark) .border-gray-800\\/60 { border-color: rgba(203, 213, 225, 0.6) !important; }
        :root:not(.dark) .border-gray-700 { border-color: #cbd5e1 !important; }
        :root:not(.dark) .border-gray-855 { border-color: #cbd5e1 !important; }
        :root:not(.dark) .border-gray-850 { border-color: #cbd5e1 !important; }
        
        :root:not(.dark) .divide-gray-800 > :not([hidden]) ~ :not([hidden]) { border-color: #cbd5e1 !important; }
        :root:not(.dark) .hover\\:bg-gray-800\\/40:hover { background-color: rgba(226, 232, 240, 0.4) !important; }
        
        /* Overriding inline styling for border-bottoms / tops on charts and cards */
        :root:not(.dark) [style*="border-bottom: 1px solid #1f2937"],
        :root:not(.dark) [style*="border-bottom:1px solid #1f2937"] {
            border-bottom: 1px solid #cbd5e1 !important;
        }
        :root:not(.dark) [style*="border-top: 1px solid #1f2937"],
        :root:not(.dark) [style*="border-top:1px solid #1f2937"] {
            border-top: 1px solid #cbd5e1 !important;
        }
        :root:not(.dark) [style*="background-color: rgba(17,24,39,0.3)"],
        :root:not(.dark) [style*="background-color:rgba(17,24,39,0.3)"] {
            background-color: rgba(226, 232, 240, 0.3) !important;
            border-color: #cbd5e1 !important;
        }
        :root:not(.dark) [style*="background-color: rgba(17,24,39,0.5)"],
        :root:not(.dark) [style*="background-color:rgba(17,24,39,0.5)"] {
            background-color: rgba(226, 232, 240, 0.45) !important;
            border-color: #cbd5e1 !important;
        }

        /* Leaderboard table overrides */
        :root:not(.dark) .table-container {
            background-color: rgba(255, 255, 255, 0.8) !important;
            border-color: #cbd5e1 !important;
        }
        :root:not(.dark) #video-table-body {
            background-color: rgba(255, 255, 255, 0.5) !important;
        }
        
        /* Specific light-mode rules for tabs & switchers */
        :root:not(.dark) #month-tabs { background-color: #f1f5f9 !important; border-color: #cbd5e1 !important; }
        
        /* Language switcher overrides */
        :root:not(.dark) [style*="background-color: #111827"],
        :root:not(.dark) [style*="background-color:#111827"] {
            background-color: #f1f5f9 !important;
            border-color: #cbd5e1 !important;
        }
        :root:not(.dark) #lang-switch-btn { background-color: #cbd5e1 !important; }
        :root:not(.dark) #lang-switch-btn span { background-color: #4f46e5 !important; }
        :root:not(.dark) #lang-label-vi { color: #475569 !important; }
        :root:not(.dark) #lang-label-en { color: #475569 !important; }
        :root:not(.dark) #lang-label-vi[style*="font-weight: 700"],
        :root:not(.dark) #lang-label-vi[style*="font-weight:700"] { color: #4f46e5 !important; }
        :root:not(.dark) #lang-label-en[style*="font-weight: 700"],
        :root:not(.dark) #lang-label-en[style*="font-weight:700"] { color: #4f46e5 !important; }

        /* Premium Pill Switchers (Demographics & Sorting Buttons) */
        #tab-demo-btn, #tab-geo-btn,
        #sort-views-btn, #sort-ret-btn {
            transition: all 0.2s ease-in-out;
        }
        :root.dark #tab-demo-btn.active, :root.dark #tab-geo-btn.active,
        :root.dark #sort-views-btn.active, :root.dark #sort-ret-btn.active {
            background-color: #6366f1 !important;
            color: #ffffff !important;
            border-color: #6366f1 !important;
            box-shadow: 0 0 10px rgba(99, 102, 241, 0.4) !important;
        }
        :root:not(.dark) #tab-demo-btn.active, :root:not(.dark) #tab-geo-btn.active,
        :root:not(.dark) #sort-views-btn.active, :root:not(.dark) #sort-ret-btn.active {
            background-color: #4f46e5 !important;
            color: #ffffff !important;
            border-color: #4f46e5 !important;
            box-shadow: 0 0 10px rgba(79, 70, 229, 0.2) !important;
        }
        :root.dark #tab-demo-btn:not(.active), :root.dark #tab-geo-btn:not(.active),
        :root.dark #sort-views-btn:not(.active), :root.dark #sort-ret-btn:not(.active) {
            background-color: #1f2937 !important;
            color: #9ca3af !important;
            border: 1px solid #374151 !important;
        }
        :root:not(.dark) #tab-demo-btn:not(.active), :root:not(.dark) #tab-geo-btn:not(.active),
        :root:not(.dark) #sort-views-btn:not(.active), :root:not(.dark) #sort-ret-btn:not(.active) {
            background-color: #f1f5f9 !important;
            color: #475569 !important;
            border: 1px solid #cbd5e1 !important;
        }
        :root.dark #tab-demo-btn:not(.active):hover, :root.dark #tab-geo-btn:not(.active):hover,
        :root.dark #sort-views-btn:not(.active):hover, :root.dark #sort-ret-btn:not(.active):hover {
            background-color: #374151 !important;
            color: #ffffff !important;
        }
        :root:not(.dark) #tab-demo-btn:not(.active):hover, :root:not(.dark) #tab-geo-btn:not(.active):hover,
        :root:not(.dark) #sort-views-btn:not(.active):hover, :root:not(.dark) #sort-ret-btn:not(.active):hover {
            background-color: #e2e8f0 !important;
            color: #0f172a !important;
        }

        /* Table sorting buttons & Search input overrides */
        :root:not(.dark) #table-search {
            background-color: #ffffff !important;
            border-color: #cbd5e1 !important;
            color: #0f172a !important;
        }
        :root:not(.dark) #table-search::placeholder {
            color: #94a3b8 !important;
        }
        
        /* Tip & summary boxes styled class */
        .chart-tip-box, .audience-summary-box {
            transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
        }
        :root:not(.dark) .chart-tip-box {
            background-color: rgba(226, 232, 240, 0.45) !important;
            border: 1px solid #cbd5e1 !important;
            color: #334155 !important;
        }
        :root:not(.dark) .audience-summary-box {
            background-color: rgba(226, 232, 240, 0.3) !important;
            border-color: #cbd5e1 !important;
            border-top: 1px solid #cbd5e1 !important;
            color: #0f172a !important;
        }
        :root:not(.dark) .audience-summary-box .text-gray-400 {
            color: #475569 !important;
        }
        :root:not(.dark) .audience-summary-box .text-white {
            color: #0f172a !important;
        }
    </style>
</head>
<body class="min-h-screen">

    <!-- Header -->
    <header class="border-b border-gray-800 bg-[#0d1321] py-5 px-4 md:px-8 md:sticky md:top-0 z-50 shadow-md">
        <div class="header-container max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div class="flex items-center gap-3" style="display: flex; align-items: center; gap: 12px;">
                <img src="assets/logo_murrplastik_vn_v2.png" alt="Logo Murrplastik" class="w-14 h-14 rounded-lg object-contain shadow-lg" style="width: 56px; height: 56px; border-radius: 8px; flex-shrink: 0; object-fit: contain;">
                <div>
                    <h1 class="text-xl md:text-2xl font-extrabold tracking-tight text-white" style="margin:0; font-size: 20px; font-weight: 800;" data-i18n="title">PHÂN TÍCH HIỆU QUẢ TRUYỀN THÔNG</h1>
                    <p class="text-xs md:text-sm text-gray-400 font-medium" style="margin:0; font-size: 13px;" data-i18n="subtitle">{REPORT_SUBTITLE_VI_FMT}</p>
                </div>
            </div>
            
            <div class="flex flex-wrap items-center gap-3 w-full md:w-auto justify-between md:justify-end" style="display: flex; align-items: center; gap: 12px;">
                <!-- Month Switcher Tabs -->
                <div id="month-tabs" class="flex items-center gap-1 bg-gray-950 px-2 py-1.5 rounded-full border border-gray-800 select-none shadow-inner" style="display: flex; align-items: center; gap: 4px; background-color: #0b0f19; padding: 4px 6px; border-radius: 9999px; border: 1px solid #1f2937;">
                    <!-- Dynamic Month Buttons will be injected here -->
                </div>

                <!-- Cần gạt ngôn ngữ -->
                <div class="flex items-center gap-2.5 bg-gray-900/80 px-3.5 py-2 rounded-full border border-gray-700 select-none shadow-inner" style="display: flex; align-items: center; gap: 10px; background-color: #111827; padding: 6px 14px; border-radius: 9999px; border: 1px solid #374151;">
                    <span id="lang-label-vi" class="text-xs font-bold text-indigo-400 cursor-pointer" style="font-size: 12px; cursor: pointer; color: #818cf8; font-weight: 700;" onclick="setLanguage('vi')">VI</span>
                    <button id="lang-switch-btn" class="relative inline-flex h-5.5 w-10 items-center rounded-full bg-gray-700 transition-colors focus:outline-none" style="position: relative; width: 40px; height: 22px; border-radius: 9999px; background-color: #4b5563; border: none; cursor: pointer;" onclick="toggleLanguage()">
                        <span id="lang-dot" class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform translate-x-1 shadow-md" style="display: inline-block; width: 16px; height: 16px; border-radius: 9999px; background-color: white; transform: translateX(4px); transition: transform 0.2s;"></span>
                    </button>
                    <span id="lang-label-en" class="text-xs font-semibold text-gray-400 cursor-pointer" style="font-size: 12px; cursor: pointer; color: #9ca3af;" onclick="setLanguage('en')">EN</span>
                </div>

                <!-- Nút bật tắt Theme sáng/tối -->
                <button id="theme-toggle-btn" class="flex items-center gap-1.5 px-3 py-1.5 rounded-full border select-none cursor-pointer transition-colors shadow-sm font-semibold" style="height: 38px; cursor: pointer; border-radius: 9999px;" onclick="toggleTheme()" title="Đổi giao diện Sáng/Tối">
                    <!-- SVG Light bulb icon and label text will be injected by JS -->
                </button>

                <div class="flex items-center gap-2" style="display: flex; align-items: center; gap: 8px;">
                    <span class="px-3.5 py-1.5 bg-green-500/10 text-green-400 rounded-full text-xs font-bold border border-green-500/25 flex items-center gap-1.5 shadow-sm" style="background-color: rgba(16,185,129,0.1); color:#34d399; padding: 6px 14px; border-radius: 9999px; font-size: 12px; border: 1px solid rgba(16,185,129,0.25);">
                        <span class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" style="display:inline-block; width:6px; height:6px; border-radius:9999px; background-color:#34d399;"></span>
                        <span data-i18n="status">Hoàn tất</span>
                    </span>
                    <span class="text-xs text-gray-400 font-medium bg-gray-900/60 px-2.5 py-1.5 rounded border border-gray-800" style="font-size:12px; color:#9ca3af; background-color: rgba(17,24,39,0.6); padding:6px 10px; border-radius:4px; border: 1px solid #1f2937;"><span data-i18n="updated">Cập nhật:</span> <span id="report-update-date">{REPORT_DATE_FMT}</span></span>
                </div>
            </div>
        </div>
    </header>

    <!-- iOS Document QuickLook / Standalone warning -->
    <div id="js-warning" style="background-color: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.25); color: #f87171; padding: 14px 16px; border-radius: 8px; margin: 16px 16px 0 16px; font-size: 13px; font-weight: bold; line-height: 1.5; max-width: 1200px;">
        💡 <strong>Mẹo xem trên điện thoại:</strong> Nếu không thấy biểu đồ tương tác hiển thị, bạn hãy nhấn nút <strong>Chia sẻ (biểu tượng Hộp có mũi tên [↑] ở dưới cùng màn hình)</strong> rồi chọn <strong>"Mở bằng Safari"</strong> hoặc <strong>"Mở bằng Chrome"</strong> để xem báo cáo tối ưu nhất!
    </div>

    <main class="max-w-7xl mx-auto px-4 py-8 md:px-8">
        
        <!-- Wrapper cho báo cáo tháng đơn lẻ -->
        <div id="monthly-report-content" class="space-y-8">

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
                        <h3 class="text-lg md:text-xl font-bold text-white" style="margin:0; font-size: 18px;" data-i18n="chart_ret_title">Biểu Đồ Tỉ Lệ Giữ Chân Người Xem</h3>
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
                
                <div class="mt-4 text-xs text-gray-400 font-semibold flex flex-col gap-y-1.5 bg-gray-900/50 p-3 rounded-lg border border-gray-800 chart-tip-box" style="margin-top: 16px; background-color: rgba(17,24,39,0.5); padding: 12px; border-radius: 8px; border: 1px solid #1f2937; width: 100%;">
                    <span data-i18n="chart_tip">💡 <strong>Mẹo:</strong> 40 điểm quãng biểu thị thời gian video được phân bổ đều từ 0% đến 100%.</span>
                    <span data-i18n="chart_avg_note">📈 Đường nét đứt biểu thị tỉ lệ giữ chân trung bình của tất cả video.</span>
                </div>
            </div>

            <!-- Right Chart: Demographics & Geography -->
            <div class="card glass-panel rounded-xl p-5 shadow-2xl flex flex-col justify-between" style="display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div class="flex items-center justify-between border-b border-gray-800 pb-4 mb-4" style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1f2937; padding-bottom:16px; margin-bottom:16px;">
                        <h3 class="text-lg md:text-xl font-bold text-white" style="margin:0; font-size:18px;" data-i18n="audience_title">Phân Khúc Người Xem</h3>
                        <div class="flex gap-1.5" style="display:flex; gap:6px;">
                            <button id="tab-demo-btn" class="active px-3 py-1.5 text-xs font-bold bg-indigo-600 text-white rounded-lg transition-colors" style="padding: 6px 12px; border-radius: 6px; border: none; font-size: 11px; cursor: pointer;" data-i18n="audience_demo_btn">Độ tuổi/Giới tính</button>
                            <button id="tab-geo-btn" class="px-3 py-1.5 text-xs font-bold bg-gray-800 text-gray-300 hover:bg-gray-700 rounded-lg transition-colors" style="padding: 6px 12px; border-radius: 6px; border: none; font-size: 11px; cursor: pointer;" data-i18n="audience_geo_btn">Quốc gia</button>
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

                <div class="border-t border-gray-800 pt-4 mt-4 text-sm font-semibold text-gray-300 bg-gray-900/30 p-3 rounded-lg border border-gray-850 audience-summary-box" style="margin-top:16px; border-top:1px solid #1f2937; background-color: rgba(17,24,39,0.3); padding:12px; border-radius:8px;">
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
                        <button id="sort-views-btn" class="active flex-1 sm:flex-none px-3.5 py-2.5 text-xs font-bold bg-indigo-600 text-white rounded-lg transition-colors whitespace-nowrap" style="flex:1; padding: 10px 14px; border-radius: 8px; border:none; font-size:12px; font-weight:700; cursor:pointer; white-space: nowrap;" data-i18n="table_sort_views">Xem nhiều nhất</button>
                        <button id="sort-ret-btn" class="flex-1 sm:flex-none px-3.5 py-2.5 text-xs font-bold bg-gray-800 text-gray-300 hover:bg-gray-700 rounded-lg transition-colors whitespace-nowrap" style="flex:1; padding: 10px 14px; border-radius: 8px; border:none; font-size:12px; font-weight:700; cursor:pointer; white-space: nowrap;" data-i18n="table_sort_ret">Giữ Chân 50%</button>
                    </div>
                </div>
            </div>

            <!-- Mobile scroll hint -->
            <div class="md:hidden mb-2.5 text-[11px] text-gray-400 font-semibold" style="color: #9ca3af; font-size: 11px; margin-bottom: 10px;" data-i18n="table_scroll_hint">
                👈 Vuốt ngang sang trái/phải để xem đầy đủ chỉ số giữ chân
            </div>

            <!-- Table Container (Horizontal scroll on mobile, visible on desktop for sticky headers) -->
            <div class="table-container custom-scrollbar border border-gray-800 rounded-lg bg-gray-950/20">
                <table class="w-full text-left text-sm text-gray-200">
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
        </div> <!-- Kết thúc #monthly-report-content -->

        <!-- Wrapper cho báo cáo so sánh các tháng -->
        <div id="comparison-report-content" class="space-y-8" style="display: none;">
            <!-- KPI Cards Grid: Compare Month 5 vs Month 6 -->
            <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
                <!-- Views -->
                <div class="card glass-panel rounded-xl p-5 shadow-xl relative overflow-hidden group hover:scale-[1.02] hover:shadow-[0_0_25px_rgba(99,102,241,0.15)] hover:border-indigo-500/30 hover:-translate-y-1 transition-all duration-300">
                    <div class="text-gray-400 text-xs font-bold tracking-wider uppercase mb-1" style="color:#9ca3af; font-size:11px;" data-i18n="comp_views_title">Lượt Xem (So Sánh)</div>
                    <div class="flex justify-between items-end mt-2" style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div>
                            <div class="text-xs text-gray-500 font-bold" style="font-size:10px; color:#6b7280;" data-i18n="comp_label_prev">Tháng Trước</div>
                            <div class="text-lg font-bold text-gray-400" id="comp-views-prev">-</div>
                        </div>
                        <div class="text-right" style="text-align: right;">
                            <div class="text-xs text-gray-500 font-bold" style="font-size:10px; color:#6b7280;" data-i18n="comp_label_curr">Tháng Này</div>
                            <div class="text-2xl font-black text-white" style="font-size: 24px; font-weight: 900;" id="comp-views-curr">-</div>
                        </div>
                    </div>
                    <div class="mt-3 pt-3 border-t border-gray-800/60 flex justify-between items-center text-xs" style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.05); margin-top:12px; padding-top:12px; font-size: 12px;">
                        <span class="text-gray-400" style="color:#9ca3af;" data-i18n="comp_change">Tăng trưởng MoM:</span>
                        <span id="comp-views-diff" class="px-2 py-0.5 rounded-full text-xs font-extrabold flex items-center gap-1 shadow-sm">-</span>
                    </div>
                </div>
                
                <!-- Engagement -->
                <div class="card glass-panel rounded-xl p-5 shadow-xl relative overflow-hidden group hover:scale-[1.02] hover:shadow-[0_0_25px_rgba(139,92,246,0.15)] hover:border-violet-500/30 hover:-translate-y-1 transition-all duration-300">
                    <div class="text-gray-400 text-xs font-bold tracking-wider uppercase mb-1" style="color:#9ca3af; font-size:11px;" data-i18n="comp_eng_title">Tương Tác (So Sánh)</div>
                    <div class="flex justify-between items-end mt-2" style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div>
                            <div class="text-xs text-gray-500 font-bold" style="font-size:10px; color:#6b7280;" data-i18n="comp_label_prev">Tháng Trước</div>
                            <div class="text-lg font-bold text-gray-400" id="comp-eng-prev">-</div>
                        </div>
                        <div class="text-right" style="text-align: right;">
                            <div class="text-xs text-gray-500 font-bold" style="font-size:10px; color:#6b7280;" data-i18n="comp_label_curr">Tháng Này</div>
                            <div class="text-2xl font-black text-white" style="font-size: 24px; font-weight: 900;" id="comp-eng-curr">-</div>
                        </div>
                    </div>
                    <div class="mt-3 pt-3 border-t border-gray-800/60 flex justify-between items-center text-xs" style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.05); margin-top:12px; padding-top:12px; font-size: 12px;">
                        <span class="text-gray-400" style="color:#9ca3af;" data-i18n="comp_change">Tăng trưởng MoM:</span>
                        <span id="comp-eng-diff" class="px-2 py-0.5 rounded-full text-xs font-extrabold flex items-center gap-1 shadow-sm">-</span>
                    </div>
                </div>
                
                <!-- Avg Duration -->
                <div class="card glass-panel rounded-xl p-5 shadow-xl relative overflow-hidden group hover:scale-[1.02] hover:shadow-[0_0_25px_rgba(6,182,212,0.15)] hover:border-cyan-500/30 hover:-translate-y-1 transition-all duration-300">
                    <div class="text-gray-400 text-xs font-bold tracking-wider uppercase mb-1" style="color:#9ca3af; font-size:11px;" data-i18n="comp_dur_title">Thời Lượng TB (So Sánh)</div>
                    <div class="flex justify-between items-end mt-2" style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div>
                            <div class="text-xs text-gray-500 font-bold" style="font-size:10px; color:#6b7280;" data-i18n="comp_label_prev">Tháng Trước</div>
                            <div class="text-lg font-bold text-gray-400" id="comp-dur-prev">-</div>
                        </div>
                        <div class="text-right" style="text-align: right;">
                            <div class="text-xs text-gray-500 font-bold" style="font-size:10px; color:#6b7280;" data-i18n="comp_label_curr">Tháng Này</div>
                            <div class="text-2xl font-black text-white" style="font-size: 24px; font-weight: 900;" id="comp-dur-curr">-</div>
                        </div>
                    </div>
                    <div class="mt-3 pt-3 border-t border-gray-800/60 flex justify-between items-center text-xs" style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.05); margin-top:12px; padding-top:12px; font-size: 12px;">
                        <span class="text-gray-400" style="color:#9ca3af;" data-i18n="comp_change">Thay đổi:</span>
                        <span id="comp-dur-diff" class="px-2 py-0.5 rounded-full text-xs font-extrabold flex items-center gap-1 shadow-sm">-</span>
                    </div>
                </div>
                
                <!-- Engagement Rate -->
                <div class="card glass-panel rounded-xl p-5 shadow-xl relative overflow-hidden group hover:scale-[1.02] hover:shadow-[0_0_25px_rgba(16,185,129,0.15)] hover:border-emerald-500/30 hover:-translate-y-1 transition-all duration-300">
                    <div class="text-gray-400 text-xs font-bold tracking-wider uppercase mb-1" style="color:#9ca3af; font-size:11px;" data-i18n="comp_rate_title">Tỷ Lệ Tương Tác (So Sánh)</div>
                    <div class="flex justify-between items-end mt-2" style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div>
                            <div class="text-xs text-gray-500 font-bold" style="font-size:10px; color:#6b7280;" data-i18n="comp_label_prev">Tháng Trước</div>
                            <div class="text-lg font-bold text-gray-400" id="comp-rate-prev">-</div>
                        </div>
                        <div class="text-right" style="text-align: right;">
                            <div class="text-xs text-gray-500 font-bold" style="font-size:10px; color:#6b7280;" data-i18n="comp_label_curr">Tháng Này</div>
                            <div class="text-2xl font-black text-white" style="font-size: 24px; font-weight: 900;" id="comp-rate-curr">-</div>
                        </div>
                    </div>
                    <div class="mt-3 pt-3 border-t border-gray-800/60 flex justify-between items-center text-xs" style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.05); margin-top:12px; padding-top:12px; font-size: 12px;">
                        <span class="text-gray-400" style="color:#9ca3af;" data-i18n="comp_change_diff">Chênh lệch MoM:</span>
                        <span id="comp-rate-diff" class="px-2 py-0.5 rounded-full text-xs font-extrabold flex items-center gap-1 shadow-sm">-</span>
                    </div>
                </div>
            </section>
            
            <!-- Charts Section -->
            <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; margin-bottom: 32px;">
                <!-- Overlaid Retention curves -->
                <div class="card glass-panel rounded-xl p-5 shadow-2xl">
                    <div class="border-b border-gray-800 pb-4 mb-5" style="border-bottom: 1px solid #1f2937; padding-bottom: 16px; margin-bottom: 20px;">
                        <h3 class="text-lg md:text-xl font-bold text-white" style="margin:0; font-size:18px;" data-i18n="comp_chart_ret_title">So Sánh Giữ Chân Người Xem TB</h3>
                        <p class="text-xs md:text-sm text-gray-400 font-medium mt-1" style="margin:0; color:#9ca3af; font-size: 13px;" data-i18n="comp_chart_ret_sub">Đường cong giữ chân trung bình của các tháng để đối chiếu chất lượng video</p>
                    </div>
                    <div style="height: 320px; position: relative;">
                        <canvas id="comparisonRetentionChart"></canvas>
                    </div>
                </div>
                
                <!-- Monthly trend bar chart (Views & Engagement side-by-side) -->
                <div class="card glass-panel rounded-xl p-5 shadow-2xl">
                    <div class="border-b border-gray-800 pb-4 mb-5" style="border-bottom: 1px solid #1f2937; padding-bottom: 16px; margin-bottom: 20px;">
                        <h3 class="text-lg md:text-xl font-bold text-white" style="margin:0; font-size:18px;" data-i18n="comp_chart_trend_title">Xu Hướng Lượt Xem & Tương Tác</h3>
                        <p class="text-xs md:text-sm text-gray-400 font-medium mt-1" style="margin:0; color:#9ca3af; font-size: 13px;" data-i18n="comp_chart_trend_sub">Biểu đồ so sánh tổng lượt xem và tương tác của các tháng</p>
                    </div>
                    <div style="height: 320px; position: relative;">
                        <canvas id="comparisonTrendChart"></canvas>
                    </div>
                </div>
            </section>
            
            <!-- Comparison Table -->
            <section class="card glass-panel rounded-xl p-5 shadow-2xl overflow-hidden mb-8">
                <div class="border-b border-gray-800 pb-4 mb-5" style="border-bottom: 1px solid #1f2937; padding-bottom: 16px; margin-bottom: 20px;">
                    <h3 class="text-lg md:text-xl font-bold text-white" style="margin:0; font-size:18px;" data-i18n="comp_table_title">Bảng Tổng Hợp So Sánh Chỉ Số Các Tháng</h3>
                    <p class="text-xs md:text-sm text-gray-400 font-medium mt-1" style="margin:0; color:#9ca3af; font-size: 13px;" data-i18n="comp_table_sub">Chi tiết số liệu thống kê tổng hợp của các tháng</p>
                </div>
                <div class="overflow-x-auto" style="overflow-x: auto; width: 100%;">
                    <table style="width: 100%; border-collapse: separate; border-spacing: 0;">
                        <thead>
                            <tr class="bg-[#0d1321]">
                                <th class="py-3.5 px-4 text-left font-bold text-white text-xs uppercase tracking-wider min-w-[120px]" data-i18n="comp_th_month">Tháng</th>
                                <th class="py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[100px]" data-i18n="comp_th_videos">Số Video</th>
                                <th class="py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[125px]" data-i18n="comp_th_views">Tổng Lượt Xem</th>
                                <th class="py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[125px]" data-i18n="comp_th_reach">Lượt Tiếp Cận</th>
                                <th class="py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[125px]" data-i18n="comp_th_eng">Lượt Tương Tác</th>
                                <th class="py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[125px]" data-i18n="comp_th_rate">Tỷ Lệ Tương Tác</th>
                                <th class="py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[120px]" data-i18n="comp_th_dur">Thời Lượng TB</th>
                                <th class="py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[140px]" data-i18n="comp_th_ret50">Giữ Chân 50% TB</th>
                                <th class="py-3.5 px-3 text-right font-bold text-white text-xs uppercase tracking-wider min-w-[140px]" data-i18n="comp_th_ret100">Giữ Chân 100% TB</th>
                            </tr>
                        </thead>
                        <tbody id="comparison-table-body" class="divide-y divide-gray-800 bg-[#090d16]/30">
                            <!-- Dynamic rows will be injected here -->
                        </tbody>
                    </table>
                </div>
            </section>
        </div> <!-- Kết thúc #comparison-report-content -->

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

        const dbAll = __REPORT_DATA__;
        const months = Object.keys(dbAll).sort((a, b) => b - a);
        let activeMonth = months[0] || "6";
        let db = dbAll[activeMonth];
        let currentLang = 'vi';

        function renderMonthTabs() {
            const tabContainer = document.getElementById('month-tabs');
            if (!tabContainer) return;
            
            tabContainer.innerHTML = '';
            
            const sortedMonths = Object.keys(dbAll).sort((a, b) => b - a);
            
            sortedMonths.forEach(m => {
                const btn = document.createElement('button');
                btn.id = `tab-month-${m}`;
                btn.onclick = () => switchMonth(m);
                btn.className = "month-tab-btn px-3 py-1 text-xs font-bold rounded-full border-0 cursor-pointer transition-all duration-200";
                btn.dataset.month = m;
                tabContainer.appendChild(btn);
            });

            // Thêm nút tab So Sánh
            if (sortedMonths.length >= 2) {
                const compBtn = document.createElement('button');
                compBtn.id = 'tab-compare-btn';
                compBtn.onclick = () => switchMonth('compare');
                compBtn.className = "month-tab-btn px-3 py-1 text-xs font-bold rounded-full border-0 cursor-pointer transition-all duration-200";
                compBtn.dataset.month = 'compare';
                tabContainer.appendChild(compBtn);
            }
            
            updateMonthTabsUI();
        }
        
        function updateMonthTabsUI() {
            const buttons = document.querySelectorAll('.month-tab-btn');
            const monthNames = {
                "vi": { "1": "Tháng 1", "2": "Tháng 2", "3": "Tháng 3", "4": "Tháng 4", "5": "Tháng 5", "6": "Tháng 6", "7": "Tháng 7", "8": "Tháng 8", "9": "Tháng 9", "10": "Tháng 10", "11": "Tháng 11", "12": "Tháng 12", "compare": "So Sánh" },
                "en": { "1": "Jan", "2": "Feb", "3": "Mar", "4": "Apr", "5": "May", "6": "Jun", "7": "Jul", "8": "Aug", "9": "Sep", "10": "Oct", "11": "Nov", "12": "Dec", "compare": "Compare" }
            };
            
            buttons.forEach(btn => {
                const m = btn.dataset.month;
                btn.textContent = monthNames[currentLang][m] || `M${m}`;
                
                if (m === activeMonth) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
                // Clear any inline styles that might interfere with CSS class overrides
                btn.style.backgroundColor = '';
                btn.style.color = '';
                btn.style.boxShadow = '';
                btn.onmouseover = null;
                btn.onmouseout = null;
            });
        }
        
        function switchMonth(m) {
            if (m === activeMonth) return;
            activeMonth = m;
            
            updateMonthTabsUI();

            if (m === 'compare') {
                document.getElementById('monthly-report-content').style.display = 'none';
                document.getElementById('comparison-report-content').style.display = 'block';
                showComparisonView();
                return;
            } else {
                document.getElementById('comparison-report-content').style.display = 'none';
                document.getElementById('monthly-report-content').style.display = 'block';
                db = dbAll[activeMonth];
            }
            
            // Cập nhật ngày báo cáo
            document.getElementById('report-update-date').textContent = db.report_date;
            
            // Cập nhật KPIs
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
            
            // Cập nhật top demographics
            let topDemoKey = "";
            let topDemoVal = -1;
            for (let k in db.demo_totals) {
                if (db.demo_totals[k] > topDemoVal) {
                    topDemoVal = db.demo_totals[k];
                    topDemoKey = k;
                }
            }
            if (topDemoKey) {
                const demoGender = topDemoKey.split('_')[0] === 'M' ? i18n[currentLang].gender_male : i18n[currentLang].gender_female;
                const demoAge = topDemoKey.replace('M_', '').replace('F_', '').replace('_plus', '+').replace('_', '-');
                const suffix = i18n[currentLang].age_suffix;
                document.getElementById('audience-top-value').textContent = `${demoGender}, ${demoAge}${suffix}`;
            }
            
            // Tái dựng dropdowns
            rebuildDropdowns();
            
            // Reset giá trị dropdown về video đầu tiên có retention
            const postsWithRet = db.posts.filter(p => p.has_retention);
            if (postsWithRet.length > 0) {
                document.getElementById('video-select-primary').value = postsWithRet[0].id;
                document.getElementById('video-select-secondary').value = "";
            }
            
            // Cập nhật biểu đồ & bảng xếp hạng
            updateRetentionChart();
            renderAudienceChart();
            renderTable();
        }

        // Translation Dictionary
        const i18n = {
            vi: {
                title: "PHÂN TÍCH HIỆU QUẢ TRUYỀN THÔNG",
                subtitle: "{REPORT_SUBTITLE_VI_FMT}",
                status: "Hoàn tất",
                updated: "Cập nhật:",
                kpi_views: "Tổng Số Lượt Xem",
                kpi_views_sub: "thời lượng TB",
                kpi_eng: "Lượt Tương Tác",
                kpi_eng_sub: "Tỷ lệ tương tác",
                kpi_ret50: "Giữ Chân Top (50% video)",
                kpi_ret100: "Giữ Chân Top (Cuối video)",
                chart_ret_title: "Biểu Đồ Tỉ Lệ Giữ Chân Người Xem",
                chart_ret_sub: "Xem diễn biến lượt xem qua 40 điểm mốc thời gian từ đầu đến cuối video",
                chart_compare: "-- So sánh với... --",
                chart_tip: "💡 <strong>Mẹo:</strong> 40 điểm quãng biểu thị thời gian video được phân bổ đều từ 0% đến 100%.",
                chart_avg_note: "📈 Đường nét đứt biểu thị tỉ lệ giữ chân trung bình của tất cả video.",
                audience_title: "Phân Khúc Người Xem",
                audience_demo_btn: "Độ tuổi/Giới tính",
                audience_geo_btn: "Quốc gia",
                audience_top_age: "Độ tuổi hàng đầu:",
                audience_top_country: "Quốc gia hàng đầu:",
                gender_male: "Nam",
                gender_female: "Nữ",
                table_title: "Bảng Xếp Hạng Hiệu Quả Truyền Thông",
                table_sub: "Danh sách tổng hợp hiệu quả và tỉ lệ giữ chân chi tiết",
                table_scroll_hint: "👈 Vuốt ngang sang trái/phải để xem đầy đủ chỉ số giữ chân",
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
                age_suffix: " tuổi",
                comp_views_title: "Lượt Xem (So Sánh)",
                comp_eng_title: "Tương Tác (So Sánh)",
                comp_dur_title: "Thời Lượng TB (So Sánh)",
                comp_rate_title: "Tỷ Lệ Tương Tác (So Sánh)",
                comp_label_prev: "Tháng Trước",
                comp_label_curr: "Tháng Này",
                comp_change: "Tăng trưởng MoM:",
                comp_change_diff: "Chênh lệch MoM:",
                comp_chart_ret_title: "So Sánh Giữ Chân Người Xem TB",
                comp_chart_ret_sub: "Đường cong giữ chân trung bình của các tháng để đối chiếu chất lượng video",
                comp_chart_trend_title: "Xu Hướng Lượt Xem & Tương Tác",
                comp_chart_trend_sub: "Biểu đồ so sánh tổng lượt xem và tương tác của các tháng",
                comp_table_title: "Bảng Tổng Hợp So Sánh Chỉ Số Các Tháng",
                comp_table_sub: "Chi tiết số liệu thống kê tổng hợp của các tháng",
                comp_th_month: "Tháng",
                comp_th_videos: "Số Video",
                comp_th_views: "Tổng Lượt Xem",
                comp_th_reach: "Lượt Tiếp Cận",
                comp_th_eng: "Lượt Tương Tác",
                comp_th_rate: "Tỷ Lệ Tương Tác",
                comp_th_dur: "Thời Lượng TB",
                comp_th_ret50: "Giữ Chân 50% TB",
                comp_th_ret100: "Giữ Chân 100% TB"
            },
            en: {
                title: "MEDIA PERFORMANCE ANALYSIS",
                subtitle: "{REPORT_SUBTITLE_EN_FMT}",
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
                table_scroll_hint: "👈 Swipe horizontally to view complete retention metrics",
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
                age_suffix: " yrs old",
                comp_views_title: "Views (Comparison)",
                comp_eng_title: "Engagement (Comparison)",
                comp_dur_title: "Avg Duration (Comparison)",
                comp_rate_title: "Engagement Rate (Comparison)",
                comp_label_prev: "Previous Month",
                comp_label_curr: "Current Month",
                comp_change: "MoM Growth:",
                comp_change_diff: "MoM Diff:",
                comp_chart_ret_title: "Avg Audience Retention Comparison",
                comp_chart_ret_sub: "Compare average retention curves between months to evaluate video quality",
                comp_chart_trend_title: "Views & Engagement Trends",
                comp_chart_trend_sub: "Grouped bar chart comparing total views and engagements between months",
                comp_table_title: "Monthly Metrics Comparison Summary",
                comp_table_sub: "Detailed comparison of aggregated monthly statistics",
                comp_th_month: "Month",
                comp_th_videos: "Videos",
                comp_th_views: "Total Views",
                comp_th_reach: "Total Reach",
                comp_th_eng: "Total Engagement",
                comp_th_rate: "Engagement Rate",
                comp_th_dur: "Avg Duration",
                comp_th_ret50: "Avg Ret 50%",
                comp_th_ret100: "Avg Ret 100%"
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
                'Liên kết': 'Liên kết',
                'liên kết': 'Liên kết',
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
                'Liên kết': 'Link',
                'liên kết': 'Link',
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
            if (typeof updateMonthTabsUI === 'function') {
                updateMonthTabsUI();
            }
            if (typeof updateThemeUI === 'function') {
                updateThemeUI();
            }
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

        function updateAudienceHighlight() {
            let topDemoKey = "";
            let topDemoVal = -1;
            for (let k in db.demo_totals) {
                if (db.demo_totals[k] > topDemoVal) {
                    topDemoVal = db.demo_totals[k];
                    topDemoKey = k;
                }
            }
            if (topDemoKey) {
                const demoGender = topDemoKey.split('_')[0] === 'M' ? i18n[currentLang].gender_male : i18n[currentLang].gender_female;
                const demoAge = topDemoKey.replace('M_', '').replace('F_', '').replace('_plus', '+').replace('_', '-');
                const suffix = i18n[currentLang].age_suffix;
                document.getElementById('audience-top-value').textContent = `${demoGender}, ${demoAge}${suffix}`;
            }
        }

        // Render Video dropdowns (Only for posts with retention curves)
        const primarySelect = document.getElementById('video-select-primary');
        const secondarySelect = document.getElementById('video-select-secondary');
        
        // Re-generate to map dynamic changes or updates
        function rebuildDropdowns() {
            const postsWithRet = db.posts.filter(p => p.has_retention);
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
            
            const labels = Array.from({length: 41}, (_, i) => `${Math.round(i * 2.5)}%`);
            
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
                                    color: getThemeColors().text,
                                    font: { weight: 'bold', family: 'Inter' },
                                    callback: function(value) { return value + '%'; }
                                },
                                grid: {
                                    color: getThemeColors().grid
                                }
                            },
                            x: {
                                ticks: {
                                    color: getThemeColors().text,
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
                                    color: getThemeColors().legend,
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
                        layout: {
                            padding: {
                                left: 15,
                                right: 10,
                                top: 0,
                                bottom: 0
                            }
                        },
                        scales: {
                            x: {
                                stacked: true,
                                ticks: { color: getThemeColors().text, font: { weight: 'bold', family: 'Inter' } },
                                grid: { color: getThemeColors().grid }
                            },
                            y: {
                                stacked: true,
                                ticks: { color: getThemeColors().text, font: { weight: 'bold', family: 'Inter' } },
                                grid: { display: false }
                            }
                        },
                        plugins: {
                            legend: {
                                labels: { color: getThemeColors().legend, font: { weight: 'bold', family: 'Inter' } }
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
                            borderColor: getThemeColors().border
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right',
                                labels: {
                                    color: getThemeColors().legend,
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
            const btnDemo = document.getElementById('tab-demo-btn');
            const btnGeo = document.getElementById('tab-geo-btn');
            btnDemo.classList.add('active');
            btnGeo.classList.remove('active');
            btnDemo.style.backgroundColor = '';
            btnDemo.style.color = '';
            btnGeo.style.backgroundColor = '';
            btnGeo.style.color = '';
            renderAudienceChart();
        });
        
        document.getElementById('tab-geo-btn').addEventListener('click', (e) => {
            activeAudienceTab = 'geo';
            const btnDemo = document.getElementById('tab-demo-btn');
            const btnGeo = document.getElementById('tab-geo-btn');
            btnGeo.classList.add('active');
            btnDemo.classList.remove('active');
            btnDemo.style.backgroundColor = '';
            btnDemo.style.color = '';
            btnGeo.style.backgroundColor = '';
            btnGeo.style.color = '';
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
                let badgeClass = "badge bg-gray-800/80 text-gray-300 border border-gray-700";
                if (p.post_type === 'Video') {
                    badgeClass = "badge badge-video bg-indigo-500/15 text-indigo-300 border border-indigo-500/25";
                } else if (p.post_type === 'Photo' || p.post_type === 'Ảnh') {
                    badgeClass = "badge badge-photo bg-emerald-500/15 text-emerald-300 border border-emerald-500/25";
                } else if (p.post_type === 'Shared link' || p.post_type === 'Liên kết chia sẻ' || p.post_type === 'Liên kết' || p.post_type === 'liên kết') {
                    badgeClass = "badge badge-link bg-amber-500/15 text-amber-300 border border-amber-500/25";
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
            const btnViews = document.getElementById('sort-views-btn');
            const btnRet = document.getElementById('sort-ret-btn');
            btnViews.classList.add('active');
            btnRet.classList.remove('active');
            btnViews.style.backgroundColor = '';
            btnViews.style.color = '';
            btnRet.style.backgroundColor = '';
            btnRet.style.color = '';
            renderTable();
        });
        
        document.getElementById('sort-ret-btn').addEventListener('click', (e) => {
            currentSort = 'ret';
            const btnViews = document.getElementById('sort-views-btn');
            const btnRet = document.getElementById('sort-ret-btn');
            btnRet.classList.add('active');
            btnViews.classList.remove('active');
            btnViews.style.backgroundColor = '';
            btnViews.style.color = '';
            btnRet.style.backgroundColor = '';
            btnRet.style.color = '';
            renderTable();
        });

        // Logic So Sánh Các Tháng (MoM)
        let compRetChart = null;
        let compBarChart = null;

        function showComparisonView() {
            const sortedMonths = Object.keys(dbAll).sort((a, b) => a - b);
            if (sortedMonths.length < 2) return;
            
            const prevMonthKey = sortedMonths[sortedMonths.length - 2];
            const currMonthKey = sortedMonths[sortedMonths.length - 1];
            
            const prevDb = dbAll[prevMonthKey];
            const currDb = dbAll[currMonthKey];
            
            const labelPrev = currentLang === 'vi' ? `Tháng ${prevMonthKey}` : `Month ${prevMonthKey}`;
            const labelCurr = currentLang === 'vi' ? `Tháng ${currMonthKey}` : `Month ${currMonthKey}`;
            
            document.querySelectorAll('[data-i18n="comp_label_prev"]').forEach(el => el.textContent = labelPrev);
            document.querySelectorAll('[data-i18n="comp_label_curr"]').forEach(el => el.textContent = labelCurr);
            
            // Lượt xem
            const prevViews = prevDb.summary.total_views;
            const currViews = currDb.summary.total_views;
            document.getElementById('comp-views-prev').textContent = fmt(prevViews);
            document.getElementById('comp-views-curr').textContent = fmt(currViews);
            
            let viewsDiff = prevViews > 0 ? ((currViews - prevViews) / prevViews * 100) : 0;
            updateCompBadge('comp-views-diff', viewsDiff);
            
            // Tương tác
            const prevEng = prevDb.summary.total_engagement;
            const currEng = currDb.summary.total_engagement;
            document.getElementById('comp-eng-prev').textContent = fmt(prevEng);
            document.getElementById('comp-eng-curr').textContent = fmt(currEng);
            
            let engDiff = prevEng > 0 ? ((currEng - prevEng) / prevEng * 100) : 0;
            updateCompBadge('comp-eng-diff', engDiff);
            
            // Thời lượng trung bình
            const prevDur = prevDb.summary.avg_duration;
            const currDur = currDb.summary.avg_duration;
            document.getElementById('comp-dur-prev').textContent = prevDur.toFixed(1) + 's';
            document.getElementById('comp-dur-curr').textContent = currDur.toFixed(1) + 's';
            
            let durDiff = prevDur > 0 ? ((currDur - prevDur) / prevDur * 100) : 0;
            updateCompBadge('comp-dur-diff', durDiff);
            
            // Tỷ lệ tương tác
            const prevRate = prevViews > 0 ? (prevEng / prevViews * 100) : 0;
            const currRate = currViews > 0 ? (currEng / currViews * 100) : 0;
            document.getElementById('comp-rate-prev').textContent = prevRate.toFixed(1) + '%';
            document.getElementById('comp-rate-curr').textContent = currRate.toFixed(1) + '%';
            
            let rateDiff = currRate - prevRate;
            updateCompBadge('comp-rate-diff', rateDiff, true);

            // Vẽ biểu đồ & điền bảng
            renderComparisonRetentionChart(sortedMonths);
            renderComparisonBarChart(sortedMonths);
            renderComparisonTable(sortedMonths);
        }
        
        function updateCompBadge(elementId, value, isDiffPoints = false) {
            const el = document.getElementById(elementId);
            if (!el) return;
            
            const isPositive = value >= 0;
            const sign = isPositive ? '▲' : '▼';
            const unit = isDiffPoints ? ' %' : '%';
            const formattedVal = Math.abs(value).toFixed(1) + unit;
            
            el.className = "px-2.5 py-0.5 rounded-full text-xs font-bold flex items-center gap-1 shadow-sm transition-all duration-300";
            
            const isDark = document.documentElement.classList.contains('dark');
            if (isPositive) {
                el.style.backgroundColor = isDark ? "rgba(16, 185, 129, 0.15)" : "rgba(5, 150, 105, 0.1)";
                el.style.color = isDark ? "#34d399" : "#047857";
                el.style.border = isDark ? "1px solid rgba(16, 185, 129, 0.25)" : "1px solid rgba(5, 150, 105, 0.2)";
                el.innerHTML = `<span class="w-1.5 h-1.5 rounded-full ${isDark ? 'bg-emerald-400 animate-pulse' : 'bg-emerald-600'}" style="display:inline-block; width:6px; height:6px; border-radius:9999px; background-color:${isDark ? '#34d399' : '#059669'};"></span> <span>${sign} ${formattedVal}</span>`;
            } else {
                el.style.backgroundColor = isDark ? "rgba(239, 68, 68, 0.15)" : "rgba(220, 38, 38, 0.08)";
                el.style.color = isDark ? "#f87171" : "#b91c1c";
                el.style.border = isDark ? "1px solid rgba(239, 68, 68, 0.25)" : "1px solid rgba(220, 38, 38, 0.18)";
                el.innerHTML = `<span>${sign} ${formattedVal}</span>`;
            }
        }
        
        function renderComparisonRetentionChart(sortedMonths) {
            const canvas = document.getElementById('comparisonRetentionChart');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            if (!ctx) return;
            
            if (compRetChart) {
                compRetChart.destroy();
            }
            
            const labels = Array.from({ length: 40 }, (_, i) => `${i + 1}`);
            
            const colors = {
                "5": {
                    border: "#818cf8",
                    fillStart: "rgba(129, 140, 248, 0.25)",
                    fillEnd: "rgba(129, 140, 248, 0.0)"
                },
                "6": {
                    border: "#f43f5e",
                    fillStart: "rgba(244, 63, 94, 0.25)",
                    fillEnd: "rgba(244, 63, 94, 0.0)"
                }
            };
            
            const datasets = sortedMonths.map(m => {
                const monthDb = dbAll[m];
                const borderCol = colors[m]?.border || "#3b82f6";
                
                const grad = ctx.createLinearGradient(0, 0, 0, 300);
                grad.addColorStop(0, colors[m]?.fillStart || "rgba(59, 130, 246, 0.25)");
                grad.addColorStop(1, colors[m]?.fillEnd || "rgba(59, 130, 246, 0.0)");
                
                const labelName = currentLang === 'vi' ? `Tháng ${m} (Avg)` : `Month ${m} (Avg)`;
                
                return {
                    label: labelName,
                    data: monthDb.avg_ret_curve,
                    borderColor: borderCol,
                    backgroundColor: grad,
                    fill: true,
                    borderWidth: 3,
                    pointRadius: 1,
                    pointHoverRadius: 4,
                    tension: 0.3
                };
            });
            
            compRetChart = new Chart(ctx, {
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
                                color: getThemeColors().text,
                                font: { weight: 'bold', family: 'Inter' },
                                callback: function(value) { return value + '%'; }
                            },
                            grid: {
                                color: getThemeColors().grid
                            }
                        },
                        x: {
                            ticks: {
                                color: getThemeColors().text,
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
                                color: getThemeColors().legend,
                                font: { weight: 'bold', family: 'Inter' }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.9)',
                            titleFont: { family: 'Inter', weight: 'bold' },
                            bodyFont: { family: 'Inter' },
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            callbacks: {
                                label: function(context) {
                                    return `${context.dataset.label}: ${context.raw.toFixed(1)}%`;
                                }
                            }
                        }
                    }
                }
            });
        }
        
        function renderComparisonBarChart(sortedMonths) {
            const canvas = document.getElementById('comparisonTrendChart');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            if (!ctx) return;
            
            if (compBarChart) {
                compBarChart.destroy();
            }
            
            const labels = sortedMonths.map(m => currentLang === 'vi' ? `Tháng ${m}` : `Month ${m}`);
            const viewsData = sortedMonths.map(m => dbAll[m].summary.total_views);
            const engData = sortedMonths.map(m => dbAll[m].summary.total_engagement);
            
            compBarChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: currentLang === 'vi' ? 'Tổng Lượt Xem' : 'Total Views',
                            data: viewsData,
                            backgroundColor: 'rgba(99, 102, 241, 0.85)',
                            borderColor: '#6366f1',
                            borderWidth: 1.5,
                            borderRadius: 6,
                            yAxisID: 'y-views'
                        },
                        {
                            label: currentLang === 'vi' ? 'Lượt Tương Tác' : 'Total Engagement',
                            data: engData,
                            backgroundColor: 'rgba(236, 72, 153, 0.85)',
                            borderColor: '#ec4899',
                            borderWidth: 1.5,
                            borderRadius: 6,
                            yAxisID: 'y-eng'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        'y-views': {
                            type: 'linear',
                            position: 'left',
                            ticks: {
                                color: getThemeColors().viewsTitle,
                                font: { weight: 'bold', family: 'Inter' },
                                callback: function(value) { return fmt(value); }
                            },
                            grid: {
                                color: getThemeColors().grid
                            },
                            title: {
                                display: true,
                                text: currentLang === 'vi' ? 'Lượt xem' : 'Views',
                                color: getThemeColors().viewsTitle,
                                font: { weight: 'bold', family: 'Inter' }
                            }
                        },
                        'y-eng': {
                            type: 'linear',
                            position: 'right',
                            ticks: {
                                color: getThemeColors().engTitle,
                                font: { weight: 'bold', family: 'Inter' },
                                callback: function(value) { return fmt(value); }
                            },
                            grid: {
                                drawOnChartArea: false
                            },
                            title: {
                                display: true,
                                text: currentLang === 'vi' ? 'Tương tác' : 'Engagement',
                                color: getThemeColors().engTitle,
                                font: { weight: 'bold', family: 'Inter' }
                            }
                        },
                        x: {
                            ticks: {
                                color: getThemeColors().text,
                                font: { weight: 'bold', family: 'Inter' }
                            },
                            grid: {
                                display: false
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: getThemeColors().legend,
                                font: { weight: 'bold', family: 'Inter' }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.9)',
                            titleFont: { family: 'Inter', weight: 'bold' },
                            bodyFont: { family: 'Inter' },
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1
                        }
                    }
                }
            });
        }
        
        function renderComparisonTable(sortedMonths) {
            const tbody = document.getElementById('comparison-table-body');
            if (!tbody) return;
            
            tbody.innerHTML = '';
            const displayMonths = [...sortedMonths].sort((a, b) => b - a);
            
            displayMonths.forEach(m => {
                const monthDb = dbAll[m];
                const tr = document.createElement('tr');
                tr.className = "hover:bg-gray-800/40 transition-colors border-b border-gray-800/50";
                
                const monthLabel = currentLang === 'vi' ? `Tháng ${m}` : `Month ${m}`;
                const totalVideos = monthDb.summary.total_posts;
                const totalViews = fmt(monthDb.summary.total_views);
                const totalReach = fmt(monthDb.summary.total_reach || 0);
                const totalEng = fmt(monthDb.summary.total_engagement);
                
                const engRate = monthDb.summary.total_views > 0 
                    ? (monthDb.summary.total_engagement / monthDb.summary.total_views * 100).toFixed(1) + '%' 
                    : '0%';
                
                const avgDur = monthDb.summary.avg_duration.toFixed(1) + 's';
                const avgRet50 = monthDb.summary.top_ret_50_val.toFixed(1) + '%';
                const avgRet100 = monthDb.summary.top_ret_100_val.toFixed(1) + '%';
                
                tr.innerHTML = `
                    <td class="py-4 px-4 font-bold text-white text-[13px] md:text-sm">
                        ${monthLabel}
                    </td>
                    <td class="py-4 px-3 text-right text-gray-300 font-semibold text-[13px] md:text-sm">
                        ${totalVideos}
                    </td>
                    <td class="py-4 px-3 text-right font-bold text-white text-[13px] md:text-sm">
                        ${totalViews}
                    </td>
                    <td class="py-4 px-3 text-right text-gray-300 font-semibold text-[13px] md:text-sm">
                        ${totalReach}
                    </td>
                    <td class="py-4 px-3 text-right text-gray-300 font-semibold text-[13px] md:text-sm">
                        ${totalEng}
                    </td>
                    <td class="py-4 px-3 text-right font-bold text-purple-400 text-[13px] md:text-sm">
                        ${engRate}
                    </td>
                    <td class="py-4 px-3 text-right text-gray-300 font-semibold text-[13px] md:text-sm">
                        ${avgDur}
                    </td>
                    <td class="py-4 px-3 text-right font-extrabold text-purple-300 text-[13px] md:text-sm">
                        ${avgRet50}
                    </td>
                    <td class="py-4 px-3 text-right font-extrabold text-emerald-300 text-[13px] md:text-sm">
                        ${avgRet100}
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        // Theme Toggle Logic (Light Mode Default)
        let activeTheme = 'light';

        function getThemeColors() {
            const isDark = document.documentElement.classList.contains('dark');
            return {
                text: isDark ? '#d1d5db' : '#475569',
                grid: isDark ? 'rgba(75, 85, 99, 0.15)' : 'rgba(148, 163, 184, 0.12)',
                legend: isDark ? '#ffffff' : '#0f172a',
                viewsTitle: isDark ? '#a5b4fc' : '#4f46e5',
                engTitle: isDark ? '#fbcfe8' : '#db2777',
                border: isDark ? '#0b0f19' : '#ffffff'
            };
        }

        function initTheme() {
            // Read stored theme preference, default to light
            const savedTheme = localStorage.getItem('theme') || 'light';
            activeTheme = savedTheme;
            
            if (activeTheme === 'dark') {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
            updateThemeUI();
        }

        function toggleTheme() {
            if (activeTheme === 'light') {
                document.documentElement.classList.add('dark');
                activeTheme = 'dark';
            } else {
                document.documentElement.classList.remove('dark');
                activeTheme = 'light';
            }
            localStorage.setItem('theme', activeTheme);
            updateThemeUI();
            updateChartThemes();
        }

        function updateThemeUI() {
            const btn = document.getElementById('theme-toggle-btn');
            if (!btn) return;
            
            const isVi = currentLang === 'vi';
            const labelText = activeTheme === 'dark' ? (isVi ? 'Tối' : 'Dark') : (isVi ? 'Sáng' : 'Light');
            
            if (activeTheme === 'dark') {
                btn.style.color = '#fbbf24'; 
                btn.style.backgroundColor = '#111827';
                btn.style.borderColor = '#374151';
                btn.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" style="width: 18px; height: 18px; display: block;">
                      <!-- outer rays -->
                      <path d="M12 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm5.657 2.343a1 1 0 010 1.414l-.707.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zm1.343 7.657a1 1 0 100-2h-1a1 1 0 100 2h1zm-1.343 5.657a1 1 0 01-1.414 0l-.707-.707a1 1 0 111.414-1.414l.707.707a1 1 0 010 1.414zM12 19a1 1 0 100 2 1 1 0 100-2zm-5.657-2.343a1 1 0 010-1.414l.707-.707a1 1 0 111.414 1.414l-.707.707a1 1 0 01-1.414 0zM5 12a1 1 0 100-2H4a1 1 0 100 2h1zM6.343 5.657a1 1 0 011.414 0l.707.707a1 1 0 11-1.414 1.414l-.707-.707a1 1 0 010-1.414z" />
                      <!-- bulb body -->
                      <path d="M9 12a3 3 0 013-3 3 3 0 013 3c0 .88-.38 1.72-1.03 2.3a2 2 0 00-.67 1.34V17h-2.6v-1.36a2 2 0 00-.67-1.34A3.013 3.013 0 019 12zm1 7h4v1a1 1 0 01-1 1h-2a1 1 0 01-1-1v-1z" />
                    </svg>
                    <span class="text-xs font-extrabold select-none">${labelText}</span>
                `;
            } else {
                btn.style.color = '#475569';
                btn.style.backgroundColor = '#f1f5f9';
                btn.style.borderColor = '#cbd5e1';
                btn.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" style="width: 18px; height: 18px; display: block;">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l.707-.707m2.808 13.064a3 3 0 01-1.04-2.08 5.002 5.002 0 011.04-8.58A5 5 0 0117 12c0 1.255-.47 2.45-1.31 3.351a3 3 0 01-1.04 2.08H9.663zM10 21h4" />
                    </svg>
                    <span class="text-xs font-extrabold select-none">${labelText}</span>
                `;
            }
        }

        function updateChartThemes() {
            const colors = getThemeColors();
            
            if (typeof retChart !== 'undefined' && retChart) {
                if (retChart.options.scales?.y?.ticks) retChart.options.scales.y.ticks.color = colors.text;
                if (retChart.options.scales?.y?.grid) retChart.options.scales.y.grid.color = colors.grid;
                if (retChart.options.scales?.x?.ticks) retChart.options.scales.x.ticks.color = colors.text;
                if (retChart.options.plugins?.legend?.labels) retChart.options.plugins.legend.labels.color = colors.legend;
                retChart.update();
            }
            
            if (typeof audienceChart !== 'undefined' && audienceChart) {
                if (audienceChart.options.scales?.x?.ticks) audienceChart.options.scales.x.ticks.color = colors.text;
                if (audienceChart.options.scales?.x?.grid) audienceChart.options.scales.x.grid.color = colors.grid;
                if (audienceChart.options.scales?.y?.ticks) audienceChart.options.scales.y.ticks.color = colors.text;
                if (audienceChart.options.plugins?.legend?.labels) audienceChart.options.plugins.legend.labels.color = colors.legend;
                if (audienceChart.data.datasets[0] && audienceChart.config.type === 'doughnut') {
                    audienceChart.data.datasets[0].borderColor = colors.border;
                }
                audienceChart.update();
            }
            
            if (typeof compRetChart !== 'undefined' && compRetChart) {
                if (compRetChart.options.scales?.y?.ticks) compRetChart.options.scales.y.ticks.color = colors.text;
                if (compRetChart.options.scales?.y?.grid) compRetChart.options.scales.y.grid.color = colors.grid;
                if (compRetChart.options.scales?.x?.ticks) compRetChart.options.scales.x.ticks.color = colors.text;
                if (compRetChart.options.plugins?.legend?.labels) compRetChart.options.plugins.legend.labels.color = colors.legend;
                compRetChart.update();
            }
            
            if (typeof compBarChart !== 'undefined' && compBarChart) {
                const scales = compBarChart.options.scales;
                if (scales?.['y-views']?.ticks) scales['y-views'].ticks.color = colors.viewsTitle;
                if (scales?.['y-views']?.grid) scales['y-views'].grid.color = colors.grid;
                if (scales?.['y-views']?.title) scales['y-views'].title.color = colors.viewsTitle;
                if (scales?.['y-eng']?.ticks) scales['y-eng'].ticks.color = colors.engTitle;
                if (scales?.['y-eng']?.title) scales['y-eng'].title.color = colors.engTitle;
                if (scales?.x?.ticks) scales.x.ticks.color = colors.text;
                if (compBarChart.options.plugins?.legend?.labels) compBarChart.options.plugins.legend.labels.color = colors.legend;
                compBarChart.update();
            }
        }

        // Bootstrap
        initTheme();
        renderMonthTabs();
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
    html_content = html_content.replace('{TOTAL_POSTS}', str(len(latest_posts)))
    
    # Inject actual JSON DB
    html_content = html_content.replace('__REPORT_DATA__', data_json)
    
    # Inject Fallback CSS elements
    html_content = html_content.replace('{FALLBACK_CHART_BARS}', fallback_chart_bars_html)
    html_content = html_content.replace('{FALLBACK_AUDIENCE_HTML}', fallback_audience_html)
    
    # Inject report dates and subtitles
    html_content = html_content.replace('{REPORT_DATE_FMT}', report_date)
    html_content = html_content.replace('{REPORT_SUBTITLE_VI_FMT}', report_subtitle_vi)
    html_content = html_content.replace('{REPORT_SUBTITLE_EN_FMT}', report_subtitle_en)

    with open(HTML_OUTPUT, mode='w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Generated HTML Dashboard: {HTML_OUTPUT}")

def main():
    print("Starting Facebook Video Retention Report generation...")
    
    # Parse all monthly CSV files
    monthly_posts = {}
    for m_idx, csv_path in MONTHLY_CSVS.items():
        print(f"Reading data file for Month {m_idx}: {csv_path}")
        posts = parse_csv(csv_path)
        print(f"Successfully parsed {len(posts)} videos for Month {m_idx}.")
        monthly_posts[m_idx] = posts
        
    if not monthly_posts:
        print("No videos found to process.")
        return
        
    generate_csv_summary(monthly_posts)
    generate_html_report(monthly_posts)
    print("Report generation complete!")

if __name__ == "__main__":
    main()
