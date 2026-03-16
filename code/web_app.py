#!/usr/bin/env python3
"""
多站点职位管理 Web 界面
Flask Web 应用，提供 HTML 粘贴、岗位展示、企业清单管理功能
支持多个招聘网站的数据解析
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

from database import BOSSDatabase
from parsers import get_parser, get_supported_sites

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


# ==================== 数据库连接 ====================

def get_db():
    """获取数据库连接"""
    db = BOSSDatabase(str(DB_PATH))
    if db.connect():
        # 先初始化表（如果不存在）
        db.init_tables()
        # 再添加 is_imported 列（如果需要升级旧数据库）
        db.add_is_imported_column()
    return db


# ==================== 路由定义 ====================

@app.route('/')
def index():
    """首页：HTML 粘贴页面"""
    supported_sites = get_supported_sites()
    enabled_sites = [s for s in supported_sites if s.get('enabled', False)]
    return render_template('paste.html', sites=enabled_sites)


@app.route('/parse', methods=['POST'])
def parse():
    """解析 HTML 内容"""
    html = request.form.get('html_content', '').strip()
    site_code = request.form.get('site_code', 'boss_zhipin')

    if not html:
        flash('请粘贴 HTML 内容', 'error')
        return redirect(url_for('index'))

    try:
        # 获取对应站点的解析器
        parser = get_parser(site_code)

        # 解析 HTML
        jobs = parser.parse(html, source='web_paste')

        if not jobs:
            flash('未找到职位信息，请检查粘贴的内容是否正确', 'error')
            return redirect(url_for('index'))

        # 存入数据库
        db = get_db()
        if not db.conn:
            flash('数据库连接失败', 'error')
            return redirect(url_for('index'))

        # 添加采集时间
        collection_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        for job in jobs:
            job['collection_time'] = collection_time

        # 批量插入
        company_count, job_count = db.insert_jobs_batch(jobs)
        db.close()

        site_name = parser.SITE_NAME
        flash(f'成功从 {site_name} 解析 {job_count} 个职位，来自 {company_count} 家企业', 'success')
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


@app.route('/companies/toggle-discard', methods=['POST'])
def toggle_company_discarded():
    """切换企业废弃状态"""
    company_id = request.json.get('company_id')

    if not company_id:
        return jsonify({'success': False, 'error': '缺少企业 ID'})

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    new_status = db.toggle_company_discarded(company_id)
    db.close()

    if new_status is None:
        return jsonify({'success': False, 'error': '更新失败'})

    return jsonify({'success': True, 'is_discarded': new_status})


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
    print("\n访问地址: http://localhost:5001")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 60)

    # 确保数据库存在并初始化
    db = get_db()
    if db.conn:
        db.close()

    # 启动 Flask 开发服务器
    app.run(debug=True, host='127.0.0.1', port=5001)


if __name__ == '__main__':
    main()
