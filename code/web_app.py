#!/usr/bin/env python3
"""
BOSS 直聘 Web 管理界面
Flask Web 应用，提供 HTML 粘贴、岗位展示、企业清单管理功能
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from bs4 import BeautifulSoup

from database import BOSSDatabase

# 创建 Flask 应用
app = Flask(__name__)
app.secret_key = 'boss-zhipin-web-ui-dev-key-2026'

# 获取基础目录（支持开发环境和打包后的 exe 环境）
if getattr(sys, 'frozen', False):
    # 打包后的 exe 环境
    BASE_DIR = Path(sys.executable).parent
else:
    # 开发环境
    BASE_DIR = Path(__file__).parent.parent

DB_PATH = BASE_DIR / "data" / "boss_jobs.db"


# ==================== HTML 解析函数（复用 extract_jobs_v6.py 逻辑）====================

def clean_salary(salary):
    """清理薪资中的特殊字符，将 BOSS 直聘的数字字体图标转换为正常数字"""
    if not salary:
        return ''

    # BOSS 直聘的 Unicode 私有区数字映射 (E031-E03A -> 1-0)
    digit_map = {
        '\ue031': '1',
        '\ue032': '2',
        '\ue033': '3',
        '\ue034': '4',
        '\ue035': '5',
        '\ue036': '6',
        '\ue037': '7',
        '\ue038': '8',
        '\ue039': '9',
        '\ue03a': '0',
    }

    # 替换私有区数字字符
    for char, digit in digit_map.items():
        salary = salary.replace(char, digit)

    # 清理其他私有区字符
    salary = re.sub(r'[\ue000-\uf8ff]', '', salary)

    return salary.strip()


def parse_html_content(html: str, source: str = 'web_paste') -> Tuple[List[Dict], List[Dict]]:
    """
    解析 HTML 内容，提取职位和企业信息

    Args:
        html: HTML 源码字符串
        source: 数据来源标识

    Returns:
        (jobs, companies): 职位和企业数据列表
    """
    soup = BeautifulSoup(html, 'html.parser')
    jobs = []

    # 查找所有岗位卡片
    cards = soup.find_all('li', class_='job-card-box')

    if not cards:
        raise ValueError("未找到岗位卡片，请确认粘贴的是完整的 BOSS 直聘搜索结果页面源码")

    for card in cards:
        try:
            # 提取岗位名称
            job_name_tag = card.find('a', class_='job-name')
            job_name = job_name_tag.get_text(strip=True) if job_name_tag else ''

            # 提取薪资
            salary_tag = card.find('span', class_='job-salary')
            salary = clean_salary(salary_tag.get_text(strip=True) if salary_tag else '')

            # 提取公司名称
            company_tag = card.find('span', class_='boss-name')
            company = company_tag.get_text(strip=True) if company_tag else ''

            # 提取公司 URL
            company_url = ''
            boss_info_tag = card.find('a', class_='boss-info')
            if boss_info_tag and boss_info_tag.get('href'):
                href = boss_info_tag.get('href')
                if href and not href.startswith('javascript:'):
                    company_url = f"https://www.zhipin.com{href}"

            # 提取地点
            location_tag = card.find('span', class_='company-location')
            location = location_tag.get_text(strip=True) if location_tag else ''

            # 提取经验和学历
            tags = card.find_all('li')
            experience = ''
            education = ''

            for tag in tags:
                text = tag.get_text(strip=True)
                if not text:
                    continue

                if any(keyword in text for keyword in ['经验', '年', '不限', '应届', '在校']):
                    experience = text
                elif any(keyword in text for keyword in ['学历', '本科', '大专', '硕士', '博士']):
                    education = text

            if job_name:
                job = {
                    'job_name': job_name,
                    'salary': salary,
                    'company': company,
                    'company_url': company_url,
                    'location': location,
                    'experience': experience,
                    'education': education,
                    'source': source
                }
                jobs.append(job)

        except Exception as e:
            print(f"处理岗位卡片时出错: {e}")
            continue

    # 去重
    seen = set()
    unique_jobs = []
    for job in jobs:
        key = f"{job.get('job_name')}_{job.get('company')}"
        if key not in seen and job.get('job_name'):
            seen.add(key)
            unique_jobs.append(job)

    return unique_jobs


def get_db():
    """获取数据库连接"""
    db = BOSSDatabase(str(DB_PATH))
    if db.connect():
        # 确保 is_imported 列存在
        db.add_is_imported_column()
    return db


# ==================== 路由定义 ====================

@app.route('/')
def index():
    """首页：HTML 粘贴页面"""
    return render_template('paste.html')


@app.route('/parse', methods=['POST'])
def parse():
    """解析 HTML 内容"""
    html = request.form.get('html_content', '').strip()

    if not html:
        flash('请粘贴 HTML 内容', 'error')
        return redirect(url_for('index'))

    try:
        # 解析 HTML
        jobs = parse_html_content(html, source='web_paste')

        if not jobs:
            flash('未找到职位信息，请检查粘贴的内容是否正确', 'error')
            return redirect(url_for('index'))

        # 存入数据库
        db = get_db()
        if not db.conn:
            flash('数据库连接失败', 'error')
            return redirect(url_for('index'))

        # 初始化表（如果不存在）
        db.init_tables()

        # 添加采集时间
        collection_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        for job in jobs:
            job['collection_time'] = collection_time

        # 批量插入
        company_count, job_count = db.insert_jobs_batch(jobs)
        db.close()

        flash(f'成功解析 {job_count} 个职位，来自 {company_count} 家企业', 'success')
        return redirect(url_for('jobs_list'))

    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'解析失败: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/jobs')
def jobs_list():
    """岗位明细页面"""
    db = get_db()
    if not db.conn:
        flash('数据库连接失败', 'error')
        return render_template('jobs.html', jobs=[], stats={})

    jobs = db.get_all_jobs()
    stats = db.get_total_stats()
    db.close()

    return render_template('jobs.html', jobs=jobs, stats=stats)


@app.route('/companies')
def companies_list():
    """企业清单页面"""
    filter_type = request.args.get('filter', 'all')

    db = get_db()
    if not db.conn:
        flash('数据库连接失败', 'error')
        return render_template('companies.html', companies=[], filter=filter_type)

    companies = db.get_companies_with_import_status(filter_type)
    db.close()

    return render_template('companies.html', companies=companies, filter=filter_type)


@app.route('/companies/toggle', methods=['POST'])
def toggle_company():
    """切换企业入库状态"""
    company_id = request.json.get('company_id')

    if not company_id:
        return jsonify({'success': False, 'error': '缺少企业 ID'})

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    new_status = db.toggle_company_imported(company_id)
    db.close()

    if new_status is None:
        return jsonify({'success': False, 'error': '更新失败'})

    return jsonify({'success': True, 'is_imported': new_status})


@app.route('/companies/batch-import', methods=['POST'])
def batch_import():
    """批量标记企业为已入库"""
    company_ids = request.form.getlist('company_ids')

    if not company_ids:
        return jsonify({'success': False, 'error': '未选择企业'})

    # 转换为整数
    try:
        company_ids = [int(cid) for cid in company_ids]
    except ValueError:
        return jsonify({'success': False, 'error': '无效的企业 ID'})

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    count = db.batch_import_companies(company_ids)
    db.close()

    return jsonify({'success': True, 'count': count})


# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(e):
    """404 错误"""
    return render_template('error.html', message='页面不存在'), 404


@app.errorhandler(500)
def server_error(e):
    """500 错误"""
    return render_template('error.html', message='服务器错误'), 500


# ==================== 启动应用 ====================

def main():
    """启动 Flask 开发服务器"""
    print("=" * 60)
    print("BOSS 直聘 Web 管理界面")
    print("=" * 60)
    print("\n启动服务器...")
    print(f"数据库路径: {DB_PATH}")
    print("\n访问地址: http://localhost:5000")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 60)

    # 确保数据库存在并初始化
    db = get_db()
    if db.conn:
        db.init_tables()
        db.close()

    # 启动 Flask 开发服务器
    app.run(debug=True, host='127.0.0.1', port=5001)


if __name__ == '__main__':
    main()
