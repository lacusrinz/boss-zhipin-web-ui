#!/usr/bin/env python3
"""
多站点职位管理 Web 界面
Flask Web 应用，提供 HTML 粘贴、岗位展示、企业清单管理功能
支持多个招聘网站的数据解析
"""

import sys
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from zoneinfo import ZoneInfo

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.formparser import FormDataParser
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import logging

from database import BOSSDatabase
from parsers import get_parser, get_supported_sites
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Monkey patch werkzeug 的 FormDataParser 来修复大表单数据限制
from werkzeug.formparser import default_stream_factory

original_init = FormDataParser.__init__

def patched_init(self, stream_factory=None, max_form_memory_size=None,
                 max_content_length=None, cls=None, max_form_parts=None):
    # 设置更大的默认值（如果未指定）
    if max_form_memory_size is None:
        max_form_memory_size = 100 * 1024 * 1024  # 100MB
    # 使用默认的 stream_factory
    if stream_factory is None:
        stream_factory = default_stream_factory
    original_init(self, stream_factory, max_form_memory_size,
                  max_content_length, cls, max_form_parts)

FormDataParser.__init__ = patched_init

# 创建 Flask 应用
app = Flask(__name__)
app.secret_key = 'boss-zhipin-web-ui-dev-key-2026'

# 设置最大请求内容长度为 100MB
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# 设置 werkzeug 的 form 数据内存限制（解决 413 错误）
app.config['MAX_FORM_MEMORY_SIZE'] = 100 * 1024 * 1024  # 100MB
app.config['MAX_FORM_PARTS'] = 1000  # 最大表单字段数

print(f"[CONFIG] MAX_CONTENT_LENGTH: {app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024:.0f} MB", file=sys.stderr, flush=True)
print(f"[CONFIG] MAX_FORM_MEMORY_SIZE: {app.config['MAX_FORM_MEMORY_SIZE'] / 1024 / 1024:.0f} MB", file=sys.stderr, flush=True)

# 获取基础目录（支持开发环境和打包后的 exe 环境）
if getattr(sys, 'frozen', False):
    # 打包后的 exe 环境
    BASE_DIR = Path(sys.executable).parent
else:
    # 开发环境
    BASE_DIR = Path(__file__).parent.parent

DB_PATH = BASE_DIR / "data" / "boss_jobs.db"


# ==================== Scheduler Setup ====================

def setup_scheduler():
    """
    Setup APScheduler for background monitoring tasks
    """
    # Configure jobstore to persist jobs in database
    jobstores = {
        'default': SQLAlchemyJobStore(url=f'sqlite:///{DB_PATH}')
    }

    # Configure executors
    executors = {
        'default': ThreadPoolExecutor(max_workers=5)
    }

    # Configure job defaults
    job_defaults = {
        'coalesce': True,  # Combine missed jobs into one
        'max_instances': 1,  # Only one instance of each job
        'misfire_grace_time': 300  # Grace period for missed jobs
    }

    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='Asia/Shanghai'
    )

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

    return scheduler

# Initialize scheduler
scheduler = setup_scheduler()


def ensure_scheduler_started():
    """Ensure the scheduler is started (for when running outside main())"""
    if not scheduler.running:
        try:
            scheduler.start()
            logging.info("Scheduler started")
        except Exception as e:
            logging.error(f"Failed to start scheduler: {e}")


# ==================== Monitoring Job Helper Functions ====================

def run_monitoring_task_wrapper(config_id: int):
    """
    Wrapper function for running monitoring tasks (called by scheduler)

    Args:
        config_id: Monitoring configuration ID
    """
    # Deferred import to avoid circular dependency with riskbird_monitor module
    # which imports from database and riskbird_search
    from riskbird_monitor import RiskBirdMonitor
    from feishu_service import FeishuService

    job_id = f'monitoring_{config_id}'
    db = get_db()

    if db.conn:
        try:
            # Get monitoring config to check time range
            config = db.get_monitoring_config(config_id)

            # Check if current time is within monitoring time range
            if config:
                monitoring_start_time = config.get('monitoring_start_time')
                monitoring_end_time = config.get('monitoring_end_time')

                # Check if current time is within range
                if not is_within_monitoring_hours(monitoring_start_time, monitoring_end_time):
                    logging.info(f"[{get_beijing_time_str()}] Job {job_id} skipped: outside monitoring hours ({monitoring_start_time} - {monitoring_end_time})")
                    return

            monitor = RiskBirdMonitor(db)
            result = monitor.run_monitoring_task(config_id)
            logging.info(f"[{get_beijing_time_str()}] Job {job_id} completed: {result}")

            # Record the run before closing connection
            config_name = config['config_name'] if config else f'Config {config_id}'
            run_id = db.insert_monitoring_run(
                config_id=config_id,
                config_name=config_name,
                success=result['success'],
                companies_added=result['companies_added'],
                companies_skipped=result['companies_skipped'],
                error_message=result.get('error')
            )

            # NEW: Send Feishu notification when new companies found
            if result['success'] and result['companies_added'] > 0 and config:
                if config.get('feishu_enabled'):
                    _send_feishu_notification(db, config, result, run_id)
        finally:
            db.close()

def _send_feishu_notification(db, config: Dict, result: Dict, run_id: int = None):
    """
    发送飞书通知

    Args:
        db: 数据库连接
        config: 监测配置
        result: 监测结果
        run_id: 执行记录 ID（可选）
    """
    import os
    from feishu_service import FeishuService

    try:
        # 从环境变量获取飞书凭证
        app_id = os.getenv('FEISHU_APP_ID')
        app_secret = os.getenv('FEISHU_APP_SECRET')

        if not app_id or not app_secret:
            logging.warning("飞书凭证未配置，跳过推送")
            return

        # 初始化飞书服务
        feishu = FeishuService(app_id, app_secret)

        # 获取新添加的企业
        companies = db.get_monitored_companies(
            config_id=config['id'],
            limit=result['companies_added']
        )

        if not companies:
            logging.warning("未找到企业数据，跳过推送")
            return

        # 格式化消息
        content = feishu.format_monitoring_notification(
            companies, config['config_name']
        )

        # 发送消息
        send_result = feishu.send_text_message(
            target_id=config['feishu_group_id'],
            target_type=config['feishu_target_type'],
            content=content
        )

        # 记录日志
        if 'error' in send_result:
            logging.error(f"飞书推送失败: {send_result['error']}")
            db.insert_feishu_push_log(
                config_id=config['id'],
                company_count=result['companies_added'],
                success=False,
                error_message=send_result['error']
            )
        else:
            logging.info(f"飞书推送成功: {result['companies_added']} 家企业")
            db.insert_feishu_push_log(
                config_id=config['id'],
                company_count=result['companies_added'],
                success=True
            )

    except Exception as e:
        logging.error(f"飞书推送异常: {e}")
        try:
            db.insert_feishu_push_log(
                config_id=config['id'],
                company_count=result['companies_added'],
                success=False,
                error_message=str(e)
            )
        except:
            pass  # 避免日志记录失败影响主流程

def add_monitoring_job(config_id: int, interval_minutes: int):
    """
    Add a monitoring job to the scheduler

    Args:
        config_id: Monitoring configuration ID
        interval_minutes: Interval in minutes
    """
    job_id = f'monitoring_{config_id}'

    # Check if scheduler is running
    if not scheduler.running:
        logging.warning(f"Scheduler is not running, attempting to start it")
        try:
            scheduler.start()
            logging.info(f"Scheduler started successfully")
        except Exception as e:
            logging.error(f"Failed to start scheduler: {e}")
            return False

    # Get config name from database for display
    db = get_db()
    config_name = f'Monitoring Config {config_id}'
    if db.conn:
        config = db.get_monitoring_config(config_id)
        if config:
            config_name = config['config_name']
        db.close()

    try:
        scheduler.add_job(
            func=run_monitoring_task_wrapper,  # Direct function reference for PyInstaller compatibility
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            name=config_name,
            replace_existing=True,
            args=[config_id]
        )
        logging.info(f"Added monitoring job: {job_id} (interval: {interval_minutes} min)")
        return True
    except Exception as e:
        logging.error(f"Failed to add job {job_id} to scheduler: {e}")
        return False

def remove_monitoring_job(config_id: int):
    """
    Remove a monitoring job from the scheduler

    Args:
        config_id: Monitoring configuration ID
    """
    job_id = f'monitoring_{config_id}'
    try:
        scheduler.remove_job(job_id)
        logging.info(f"Removed monitoring job: {job_id}")
        return True
    except Exception as e:
        # Job might not be in scheduler memory but could be in jobstore
        # Try to remove it directly from the database jobstore
        logging.warning(f"Failed to remove job {job_id} from scheduler: {e}")
        try:
            # Remove directly from APScheduler's jobstore table
            db = get_db()
            if db.conn:
                db.cursor.execute("DELETE FROM apscheduler_jobs WHERE id = ?", (job_id,))
                db.conn.commit()
                db.close()
                logging.info(f"Removed orphaned job record from database: {job_id}")
                return True
        except Exception as db_error:
            logging.error(f"Failed to remove job {job_id} from database: {db_error}")
            if db.conn:
                db.close()
        return False

def pause_monitoring_job(config_id: int):
    """Pause a monitoring job"""
    job_id = f'monitoring_{config_id}'
    try:
        scheduler.pause_job(job_id)
        return True
    except Exception as e:
        logging.error(f"Failed to pause job {job_id}: {e}")
        return False

def resume_monitoring_job(config_id: int):
    """Resume a paused monitoring job"""
    job_id = f'monitoring_{config_id}'
    try:
        scheduler.resume_job(job_id)
        return True
    except Exception as e:
        logging.error(f"Failed to resume job {job_id}: {e}")
        return False

def run_monitoring_job_now(config_id: int):
    """Run a monitoring job immediately by calling the wrapper function directly"""
    try:
        run_monitoring_task_wrapper(config_id)
        return True
    except Exception as e:
        logging.error(f"Failed to run job monitoring_{config_id}: {e}")
        return False


def is_within_monitoring_hours(start_time: str, end_time: str) -> bool:
    """
    Check if current Beijing time is within the monitoring time range.

    Args:
        start_time: Start time in HH:MM format (e.g., "09:00")
        end_time: End time in HH:MM format (e.g., "18:00")

    Returns:
        True if current time is within range, or if no time restriction is set
        False if current time is outside the specified range
    """
    # Return True if no time restriction (None or empty strings)
    if not start_time or not end_time:
        return True

    # Get current Beijing time
    beijing_tz = ZoneInfo("Asia/Shanghai")
    now = datetime.now(beijing_tz)
    current_time = now.strftime("%H:%M")

    # Compare times
    return start_time <= current_time <= end_time


def get_beijing_time_str() -> str:
    """
    Get current Beijing time as a formatted string.

    Returns:
        Formatted Beijing time string like "2026-03-18 14:30:00 +08:00"
    """
    beijing_tz = ZoneInfo("Asia/Shanghai")
    now = datetime.now(beijing_tz)
    return now.strftime("%Y-%m-%d %H:%M:%S %z")


# ==================== 数据库连接 ====================

# 全局初始化标志
_db_initialized = False

def _initialize_database_once():
    """只初始化一次数据库（表结构、列升级等）"""
    global _db_initialized
    if _db_initialized:
        return True

    db = BOSSDatabase(str(DB_PATH))
    if db.connect():
        # 先初始化表（如果不存在）
        db.init_tables()
        # 添加升级列
        db.add_is_imported_column()
        db.add_discarded_column()
        # 初始化监测表
        db.init_monitoring_tables()
        db.close()
        _db_initialized = True
        return True
    return False

def get_db():
    """获取数据库连接（不再重复初始化）"""
    # 确保数据库已初始化
    _initialize_database_once()

    # 创建新的数据库连接
    db = BOSSDatabase(str(DB_PATH))
    db.connect()
    return db


# ==================== 路由定义 ====================

@app.before_request
def log_request():
    """记录请求信息用于调试"""
    if request.path == '/parse':
        print(f"[REQUEST] {request.method} {request.path}")
        print(f"[REQUEST] Content-Length: {request.content_length}")
        if request.content_length:
            print(f"[REQUEST] Content-Length: {request.content_length / 1024:.2f} KB")

@app.route('/')
def index():
    """首页：HTML 粘贴页面"""
    # Ensure scheduler and database are initialized
    ensure_scheduler_started()
    _initialize_database_once()

    supported_sites = get_supported_sites()
    enabled_sites = [s for s in supported_sites if s.get('enabled', False)]
    return render_template('paste.html', sites=enabled_sites)


@app.route('/parse', methods=['POST'])
def parse():
    """解析 HTML 内容"""
    import sys
    import traceback
    try:
        print(f"[PARSE] 函数被调用了！", file=sys.stderr, flush=True)
        print(f"[PARSE] request.form keys: {list(request.form.keys())}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[PARSE] Debug error: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)

    html = request.form.get('html_content', '').strip()

    # 自动检测平台（如果用户没有手动选择）
    site_code = request.form.get('site_code', '')
    if not site_code or site_code == 'auto':
        from parsers.base import BaseParser
        detected_site = BaseParser.detect_site(html)
        if detected_site != 'unknown':
            site_code = detected_site
            print(f"[PARSE] 自动检测到平台: {site_code}", file=sys.stderr, flush=True)
        else:
            # 无法检测时使用默认值
            site_code = 'boss_zhipin'
            print(f"[PARSE] 无法检测平台，使用默认: {site_code}", file=sys.stderr, flush=True)
    else:
        print(f"[PARSE] 用户选择平台: {site_code}", file=sys.stderr, flush=True)

    print(f"[PARSE] HTML 内容大小: {len(html)} 字节 ({len(html)/1024:.2f} KB)", file=sys.stderr, flush=True)

    if not html:
        flash('请粘贴 HTML 内容', 'error')
        return redirect(url_for('index'))

    try:
        # 获取对应站点的解析器
        parser = get_parser(site_code)
        print(f"[PARSE] 解析器: {parser.SITE_NAME}", file=sys.stderr, flush=True)

        # 解析 HTML
        jobs = parser.parse(html, source='web_paste')
        print(f"[PARSE] 解析结果: {len(jobs)} 个职位", file=sys.stderr, flush=True)

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
        print(f"[PARSE] ValueError: {e}", file=sys.stderr, flush=True)
        flash(str(e), 'error')
        return redirect(url_for('index'))
    except Exception as e:
        print(f"[PARSE] Exception: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
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


# ==================== Monitoring API Endpoints ====================

def validate_time_format(time_str: str) -> bool:
    """
    Check if time string is in valid HH:MM format.

    Args:
        time_str: Time string to validate

    Returns:
        True if valid HH:MM format (00:00-23:59), False otherwise
    """
    if not time_str:
        return False
    pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
    return bool(re.match(pattern, time_str))


def validate_time_range(start: str, end: str) -> bool:
    """
    Check if time range is valid (start < end, no cross-day).

    Args:
        start: Start time in HH:MM format
        end: End time in HH:MM format

    Returns:
        True if valid range (start < end), False if cross-day or equal
    """
    if not start or not end:
        return False
    return start < end


@app.route('/api/monitoring/token', methods=['GET'])
def get_token_config():
    """Get RiskBird token configuration (masked)"""
    from token_service import TokenService

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    configs = db.get_all_riskbird_configs()
    db.close()

    # Mask token for display
    token_service = TokenService()
    masked_configs = {}
    for key, value in configs.items():
        if key == 'token':
            masked_configs[key] = token_service.mask_token(value)
        else:
            masked_configs[key] = value

    return jsonify({'success': True, 'configs': masked_configs})


@app.route('/api/monitoring/token', methods=['POST'])
def save_token_config():
    """Save RiskBird token configuration"""
    from token_service import TokenService

    data = request.json
    if data is None:
        return jsonify({'success': False, 'error': '无效的JSON数据'}), 400

    token = data.get('token', '').strip()
    app_uuid = data.get('app_uuid', '').strip()
    userinfo = data.get('userinfo', '').strip()

    if not token or not app_uuid:
        return jsonify({'success': False, 'error': 'Token和App UUID不能为空'})

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    # Encrypt and save token
    token_service = TokenService()

    if token:
        encrypted_token = token_service.encrypt(token)
        db.insert_riskbird_config('token', encrypted_token)

    if app_uuid:
        db.insert_riskbird_config('app_uuid', app_uuid)

    if userinfo:
        db.insert_riskbird_config('userinfo', userinfo)

    db.close()

    return jsonify({'success': True, 'message': '配置已保存'})


@app.route('/api/monitoring/token/test', methods=['POST'])
def test_token_connection():
    """Test RiskBird token connection"""
    from token_service import TokenService
    from riskbird_search import build_search_params, call_riskbird_search_api

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    encrypted_token = db.get_riskbird_config('token')
    app_uuid = db.get_riskbird_config('app_uuid')

    if not encrypted_token or not app_uuid:
        db.close()
        return jsonify({'success': False, 'error': '请先配置Token'})

    # Decrypt token
    token_service = TokenService()
    try:
        token = token_service.decrypt(encrypted_token)
    except Exception as e:
        db.close()
        return jsonify({'success': False, 'error': f'Token解密失败: {str(e)}'})

    db.close()

    # Test API call with minimal params - use dynamic date
    today = datetime.now().strftime('%Y-%m-%d')
    test_params = build_search_params(
        regionid='110000',
        esdate=f'{today}￥{today}'
    )

    response = call_riskbird_search_api(token, app_uuid, test_params)

    if 'error' in response:
        if response['error'] == 'unauthorized':
            return jsonify({'success': False, 'error': 'Token无效或已过期'})
        else:
            return jsonify({'success': False, 'error': f'API调用失败: {response.get("message")}'})

    return jsonify({'success': True, 'message': '连接测试成功'})


@app.route('/api/monitoring/configs', methods=['GET'])
def get_monitoring_configs():
    """Get all monitoring configurations"""
    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    configs = db.get_all_monitoring_configs()
    db.close()

    return jsonify({'success': True, 'configs': configs})


@app.route('/api/monitoring/configs/<int:config_id>', methods=['GET'])
def get_monitoring_config_detail(config_id):
    """Get a single monitoring configuration for editing"""
    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    config = db.get_monitoring_config(config_id)
    db.close()

    if not config:
        return jsonify({'success': False, 'error': '配置不存在'}), 404

    # Parse region_codes from JSON string
    import json
    try:
        config['region_codes'] = json.loads(config['region_codes'])
    except:
        config['region_codes'] = []

    return jsonify({'success': True, 'config': config})


@app.route('/api/monitoring/configs', methods=['POST'])
def create_monitoring_config():
    """Create a new monitoring configuration"""
    data = request.json
    if data is None:
        return jsonify({'success': False, 'error': '无效的JSON数据'}), 400

    config_name = data.get('config_name', '').strip()
    region_codes = data.get('region_codes', [])
    interval_minutes = data.get('interval_minutes', 5)
    reg_cap = data.get('reg_cap', '').strip()

    # Extract time range parameters with defaults
    monitoring_start_time = data.get('monitoring_start_time', '09:00').strip()
    monitoring_end_time = data.get('monitoring_end_time', '18:00').strip()

    # NEW: Feishu parameters
    feishu_enabled = data.get('feishu_enabled', False)
    feishu_target_type = data.get('feishu_target_type', '').strip()
    feishu_group_id = data.get('feishu_group_id', '').strip()

    if not config_name:
        return jsonify({'success': False, 'error': '配置名称不能为空'}), 400

    if not isinstance(region_codes, list) or not region_codes:
        return jsonify({'success': False, 'error': '地区代码必须是非空数组'}), 400

    if not isinstance(interval_minutes, int) or not (1 <= interval_minutes <= 1440):
        return jsonify({'success': False, 'error': '监控间隔必须在1-1440分钟之间'}), 400

    # Validate time format
    if not validate_time_format(monitoring_start_time):
        return jsonify({'success': False, 'error': '监控开始时间格式无效，请使用HH:MM格式（例如：09:00）'}), 400

    if not validate_time_format(monitoring_end_time):
        return jsonify({'success': False, 'error': '监控结束时间格式无效，请使用HH:MM格式（例如：18:00）'}), 400

    # Validate time range (no cross-day)
    if not validate_time_range(monitoring_start_time, monitoring_end_time):
        return jsonify({'success': False, 'error': '监控时间范围无效：结束时间必须晚于开始时间（不支持跨天）'}), 400

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'}), 500

    try:
        # Convert region list to JSON string
        import json
        region_codes_json = json.dumps(region_codes)

        config_id = db.insert_monitoring_config(
            config_name=config_name,
            region_codes=region_codes_json,
            interval_minutes=interval_minutes,
            reg_cap=reg_cap if reg_cap else None,
            monitoring_start_time=monitoring_start_time,
            monitoring_end_time=monitoring_end_time
        )

        if not config_id:
            db.close()
            return jsonify({'success': False, 'error': '创建配置失败: 数据库插入返回None'}), 500

        # NEW: Update Feishu settings if enabled
        if feishu_enabled:
            db.update_monitoring_config_feishu(
                config_id=config_id,
                feishu_enabled=True,
                feishu_target_type=feishu_target_type if feishu_target_type else None,
                feishu_group_id=feishu_group_id if feishu_group_id else None
            )

        # Add job to scheduler
        job_added = add_monitoring_job(config_id, interval_minutes)

        if not job_added:
            logging.warning(f"Failed to add scheduler job for config {config_id}")

        db.close()
        return jsonify({'success': True, 'config_id': config_id, 'job_added': job_added})

    except Exception as e:
        logging.error(f"Failed to create monitoring config: {e}", exc_info=True)
        db.close()
        return jsonify({'success': False, 'error': f'创建配置失败: {str(e)}'}), 500


@app.route('/api/monitoring/configs/<int:config_id>', methods=['PUT'])
def update_monitoring_config(config_id):
    """Update monitoring configuration"""
    data = request.json
    if data is None:
        return jsonify({'success': False, 'error': '无效的JSON数据'}), 400

    db = get_db()
    try:
        if not db.conn:
            return jsonify({'success': False, 'error': '数据库连接失败'})
        # Build update dict
        updates = {}
        if 'config_name' in data:
            config_name = data['config_name'].strip() if data['config_name'] else None
            # Convert empty string to None
            if config_name and config_name.strip():
                updates['config_name'] = config_name

        if 'region_codes' in data:
            import json
            updates['region_codes'] = json.dumps(data['region_codes'])

        if 'interval_minutes' in data:
            updates['interval_minutes'] = data['interval_minutes']

        if 'reg_cap' in data:
            reg_cap = data['reg_cap'].strip() if data['reg_cap'] else None
            # Convert empty string to None
            if reg_cap and reg_cap.strip():
                updates['reg_cap'] = reg_cap

        # Handle time range fields with validation
        monitoring_start_time = None
        monitoring_end_time = None

        if 'monitoring_start_time' in data:
            monitoring_start_time = data['monitoring_start_time'].strip() if data['monitoring_start_time'] else None
            # Convert empty string to None
            if monitoring_start_time and monitoring_start_time.strip():
                # Validate time format
                if not validate_time_format(monitoring_start_time):
                    return jsonify({'success': False, 'error': '监控开始时间格式无效，请使用HH:MM格式（例如：09:00）'}), 400
                updates['monitoring_start_time'] = monitoring_start_time
            else:
                monitoring_start_time = None

        if 'monitoring_end_time' in data:
            monitoring_end_time = data['monitoring_end_time'].strip() if data['monitoring_end_time'] else None
            # Convert empty string to None
            if monitoring_end_time and monitoring_end_time.strip():
                # Validate time format
                if not validate_time_format(monitoring_end_time):
                    return jsonify({'success': False, 'error': '监控结束时间格式无效，请使用HH:MM格式（例如：18:00）'}), 400
                updates['monitoring_end_time'] = monitoring_end_time
            else:
                monitoring_end_time = None

        # Validate time range if both times are provided
        if monitoring_start_time and monitoring_end_time:
            if not validate_time_range(monitoring_start_time, monitoring_end_time):
                return jsonify({'success': False, 'error': '监控时间范围无效：结束时间必须晚于开始时间（不支持跨天）'}), 400

        # Handle Feishu fields
        if 'feishu_enabled' in data:
            updates['feishu_enabled'] = 1 if data['feishu_enabled'] else 0

        if 'feishu_target_type' in data:
            feishu_target_type = data['feishu_target_type'].strip() if data['feishu_target_type'] else None
            if feishu_target_type and feishu_target_type.strip():
                updates['feishu_target_type'] = feishu_target_type

        if 'feishu_group_id' in data:
            feishu_group_id = data['feishu_group_id'].strip() if data['feishu_group_id'] else None
            if feishu_group_id and feishu_group_id.strip():
                updates['feishu_group_id'] = feishu_group_id

        success = db.update_monitoring_config(config_id, **updates)

        if success and 'interval_minutes' in updates:
            # Update job schedule
            remove_monitoring_job(config_id)
            add_monitoring_job(config_id, updates['interval_minutes'])

        if success:
            return jsonify({'success': True, 'message': '配置已更新'})
        else:
            return jsonify({'success': False, 'error': '更新配置失败'})

    finally:
        # Always close database connection, even on early returns
        db.close()


@app.route('/api/monitoring/configs/<int:config_id>', methods=['DELETE'])
def delete_monitoring_config(config_id):
    """Delete monitoring configuration"""
    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'}), 500

    # Remove from scheduler (now handles orphaned job records)
    job_removed = remove_monitoring_job(config_id)

    # Delete from database
    success = db.delete_monitoring_config(config_id)
    db.close()

    if success:
        return jsonify({'success': True, 'message': '配置已删除', 'job_removed': job_removed})
    else:
        return jsonify({'success': False, 'error': '删除配置失败'}), 500


@app.route('/api/monitoring/jobs', methods=['GET'])
def get_monitoring_jobs():
    """Get all monitoring jobs status"""
    jobs = scheduler.get_jobs()

    # Get database connection to fetch time range info
    db = get_db()

    job_list = []
    for job in jobs:
        if job.id.startswith('monitoring_'):
            config_id = int(job.id.split('_')[1])

            # Get config to retrieve time range
            config = None
            if db.conn:
                config = db.get_monitoring_config(config_id)

            job_data = {
                'id': job.id,
                'config_id': config_id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'paused': not job.next_run_time
            }

            # Add time range fields if config exists
            if config:
                job_data['monitoring_start_time'] = config.get('monitoring_start_time')
                job_data['monitoring_end_time'] = config.get('monitoring_end_time')

            job_list.append(job_data)

    if db.conn:
        db.close()

    return jsonify({'success': True, 'jobs': job_list})


@app.route('/api/monitoring/jobs/<int:config_id>/toggle', methods=['POST'])
def toggle_monitoring_job(config_id):
    """Toggle monitoring job (pause/resume)"""
    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    config = db.get_monitoring_config(config_id)
    db.close()

    if not config:
        return jsonify({'success': False, 'error': '配置不存在'})

    # Check if job is paused
    job_id = f'monitoring_{config_id}'
    job = scheduler.get_job(job_id)

    if job:
        # Check next_run_time to determine if job is paused
        if job.next_run_time is None:
            # Already paused, resume it
            if resume_monitoring_job(config_id):
                return jsonify({'success': True, 'paused': False})
        else:
            # Running, pause it
            if pause_monitoring_job(config_id):
                return jsonify({'success': True, 'paused': True})
    else:
        return jsonify({'success': False, 'error': '任务不存在'})

    return jsonify({'success': False, 'error': '操作失败'})


@app.route('/api/monitoring/jobs/<int:config_id>/run-now', methods=['POST'])
def run_monitoring_job_now_endpoint(config_id):
    """Run monitoring job immediately"""
    success = run_monitoring_job_now(config_id)

    if success:
        return jsonify({'success': True, 'message': '任务已启动'})
    else:
        return jsonify({'success': False, 'error': '启动任务失败'})


@app.route('/api/monitoring/companies', methods=['GET'])
def get_monitored_companies():
    """Get monitored companies with pagination and date filtering"""
    config_id = request.args.get('config_id', type=int)
    start_date = request.args.get('start_date', type=str)  # 新增
    end_date = request.args.get('end_date', type=str)      # 新增
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    companies = db.get_monitored_companies(
        config_id=config_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )

    # Use filtered count to apply the same filters as the data query
    total = db.get_monitored_companies_count_filtered(
        config_id=config_id,
        start_date=start_date,
        end_date=end_date
    )

    db.close()

    return jsonify({
        'success': True,
        'companies': companies,
        'total': total,
        'limit': limit,
        'offset': offset
    })


@app.route('/api/monitoring/runs', methods=['GET'])
def get_monitoring_runs():
    """Get monitoring run records with pagination and date filtering"""
    config_id = request.args.get('config_id', type=int)
    start_date = request.args.get('start_date', type=str)  # 新增
    end_date = request.args.get('end_date', type=str)      # 新增
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    runs = db.get_monitoring_runs(
        config_id=config_id,
        start_date=start_date,  # 新增
        end_date=end_date,      # 新增
        limit=limit,
        offset=offset
    )

    # Use filtered count to apply the same filters as the data query
    total = db.get_monitoring_runs_count_filtered(
        config_id=config_id,
        start_date=start_date,
        end_date=end_date
    )
    db.close()

    return jsonify({
        'success': True,
        'runs': runs,
        'total': total,
        'limit': limit,
        'offset': offset
    })


@app.route('/api/monitoring/stats', methods=['GET'])
def get_monitoring_stats():
    """Get monitoring statistics"""
    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    stats = db.get_monitoring_stats()
    db.close()

    return jsonify({'success': True, 'stats': stats})


@app.route('/monitoring')
def monitoring_page():
    """Monitoring management page"""
    return render_template('monitoring.html')


# ==================== 错误处理 ====================

@app.errorhandler(413)
def request_entity_too_large(e):
    """413 错误 - 请求内容过大"""
    flash('粘贴的 HTML 内容太大，请减小文件大小或联系管理员增加限制', 'error')
    return redirect(url_for('index'))


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

    # 确保数据库存在并初始化（在启动时完成）
    _initialize_database_once()

    # Start scheduler
    scheduler.start()
    print("✅ 后台任务调度器已启动")

    # 启动 Flask 开发服务器
    try:
        app.run(debug=False, host='127.0.0.1', port=5001)
    finally:
        scheduler.shutdown()


@app.route('/api/monitoring/feishu/test', methods=['POST'])
def test_feishu_message():
    """Test Feishu message sending"""
    import os
    from feishu_service import FeishuService

    data = request.json
    if data is None:
        return jsonify({'success': False, 'error': '无效的JSON数据'}), 400

    target_type = data.get('target_type', '').strip()
    target_id = data.get('target_id', '').strip()

    if not target_type or not target_id:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    if target_type not in ['group', 'user']:
        return jsonify({'success': False, 'error': '目标类型必须是 group 或 user'}), 400

    try:
        # 从环境变量获取飞书凭证
        app_id = os.getenv('FEISHU_APP_ID')
        app_secret = os.getenv('FEISHU_APP_SECRET')

        if not app_id or not app_secret:
            return jsonify({'success': False, 'error': '飞书凭证未配置，请检查环境变量'}), 500

        feishu = FeishuService(app_id, app_secret)

        content = """🧪 测试消息

这是一条来自企业监测系统的测试消息。

如果你收到这条消息，说明飞书推送配置正确！"""

        result = feishu.send_text_message(target_id, target_type, content)

        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']})

        return jsonify({'success': True, 'message': '测试消息已发送'})

    except Exception as e:
        logging.error(f"测试飞书消息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    main()
