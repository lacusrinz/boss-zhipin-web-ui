#!/usr/bin/env python3
"""
数据库操作模块
使用 SQLite 存储岗位和企业信息
"""

import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Optional, Tuple


class BOSSDatabase:
    """BOSS 直聘数据库操作类"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径，默认为项目根目录下的 boss_jobs.db
        """
        if db_path is None:
            # 确定基础目录（支持开发环境和打包后的 exe 环境）
            if getattr(sys, 'frozen', False):
                # 打包后的 exe 环境
                base_dir = Path(sys.executable).parent
            else:
                # 开发环境
                base_dir = Path(__file__).parent.parent

            db_path = base_dir / "data" / "boss_jobs.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = None
        self.cursor = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA foreign_keys = ON")
            logging.debug(f"数据库连接成功: {self.db_path}")
            return True
        except Exception as e:
            logging.error(f"数据库连接失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logging.debug("数据库连接已关闭")

    def init_tables(self):
        """初始化数据库表"""
        try:
            # 创建企业表
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    url TEXT,
                    is_imported BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建岗位表
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    job_name TEXT NOT NULL,
                    salary TEXT,
                    location TEXT,
                    experience TEXT,
                    education TEXT,
                    source TEXT,
                    platform TEXT,
                    collection_time TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id),
                    CONSTRAINT unique_job_company UNIQUE (job_name, company_id)
                )
            """)

            # 创建索引
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_company_name
                ON companies(name)
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_name
                ON jobs(job_name)
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_source
                ON jobs(source)
            """)

            self.conn.commit()
            logging.info("数据库表初始化成功")
            return True

        except Exception as e:
            logging.error(f"数据库表初始化失败: {e}")
            return False

    def insert_company(self, name: str, url: str = None) -> int:
        """
        插入企业信息

        Args:
            name: 企业名称
            url: 企业 URL

        Returns:
            int: 企业 ID
        """
        try:
            # 尝试插入，如果已存在则返回现有 ID
            self.cursor.execute("""
                INSERT OR IGNORE INTO companies (name, url)
                VALUES (?, ?)
            """, (name, url))

            self.conn.commit()

            # 获取企业 ID
            self.cursor.execute("""
                SELECT id FROM companies WHERE name = ?
            """, (name,))
            result = self.cursor.fetchone()
            company_id = result[0] if result else None

            return company_id

        except Exception as e:
            logging.error(f"插入企业信息失败: {e}")
            return None

    def insert_job(self, company_id: int, job_data: Dict) -> bool:
        """
        插入岗位信息

        Args:
            company_id: 企业 ID
            job_data: 岗位数据字典

        Returns:
            bool: 是否插入成功
        """
        try:
            self.cursor.execute("""
                INSERT OR IGNORE INTO jobs
                (company_id, job_name, salary, location, experience, education, source, platform, collection_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                job_data.get('job_name', ''),
                job_data.get('salary', ''),
                job_data.get('location', ''),
                job_data.get('experience', ''),
                job_data.get('education', ''),
                job_data.get('source', ''),
                job_data.get('platform', ''),
                job_data.get('collection_time', '')
            ))

            self.conn.commit()
            return True

        except Exception as e:
            logging.error(f"插入岗位信息失败: {e}")
            return False

    def insert_jobs_batch(self, jobs: List[Dict]) -> Tuple[int, int]:
        """
        批量插入岗位信息

        Args:
            jobs: 岗位数据列表

        Returns:
            tuple: (成功插入的企业数, 成功插入的岗位数)
        """
        company_count = 0
        job_count = 0

        for job in jobs:
            try:
                # 获取或创建企业
                company_name = job.get('company', '')
                company_url = job.get('company_url', '')

                if not company_name:
                    continue

                company_id = self.insert_company(company_name, company_url)
                if company_id:
                    company_count += 1

                    # 插入岗位
                    if self.insert_job(company_id, job):
                        job_count += 1

            except Exception as e:
                logging.error(f"批量插入失败: {e}")
                continue

        return company_count, job_count

    def get_company_stats(self) -> List[Tuple]:
        """
        获取企业统计信息

        Returns:
            list: 企业统计列表 [(企业名称, 岗位数量), ...]
        """
        try:
            self.cursor.execute("""
                SELECT c.name, COUNT(j.id) as job_count
                FROM companies c
                LEFT JOIN jobs j ON c.id = j.company_id
                GROUP BY c.id, c.name
                ORDER BY job_count DESC
            """)
            return self.cursor.fetchall()
        except Exception as e:
            logging.error(f"获取企业统计失败: {e}")
            return []

    def get_source_stats(self) -> List[Tuple]:
        """
        获取来源统计信息

        Returns:
            list: 来源统计列表 [(来源, 岗位数量), ...]
        """
        try:
            self.cursor.execute("""
                SELECT source, COUNT(*) as job_count
                FROM jobs
                GROUP BY source
                ORDER BY job_count DESC
            """)
            return self.cursor.fetchall()
        except Exception as e:
            logging.error(f"获取来源统计失败: {e}")
            return []

    def get_total_stats(self) -> Dict:
        """
        获取总体统计信息

        Returns:
            dict: 统计信息字典
        """
        try:
            stats = {}

            # 企业总数
            self.cursor.execute("SELECT COUNT(*) FROM companies")
            stats['total_companies'] = self.cursor.fetchone()[0]

            # 岗位总数
            self.cursor.execute("SELECT COUNT(*) FROM jobs")
            stats['total_jobs'] = self.cursor.fetchone()[0]

            # 有 URL 的企业数
            self.cursor.execute("SELECT COUNT(*) FROM companies WHERE url IS NOT NULL AND url != ''")
            stats['companies_with_url'] = self.cursor.fetchone()[0]

            return stats

        except Exception as e:
            logging.error(f"获取总体统计失败: {e}")
            return {}

    def search_jobs(self, keyword: str = None, source: str = None, limit: int = 100) -> List[Dict]:
        """
        搜索岗位信息

        Args:
            keyword: 岗位名称关键词
            source: 数据来源
            limit: 返回结果数量限制

        Returns:
            list: 岗位信息列表
        """
        try:
            query = """
                SELECT
                    j.id,
                    j.job_name,
                    j.salary,
                    c.name as company_name,
                    c.url as company_url,
                    j.location,
                    j.experience,
                    j.education,
                    j.source,
                    j.collection_time
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE 1=1
            """
            params = []

            if keyword:
                query += " AND j.job_name LIKE ?"
                params.append(f"%{keyword}%")

            if source:
                query += " AND j.source = ?"
                params.append(source)

            query += " ORDER BY j.id DESC LIMIT ?"
            params.append(limit)

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()

            columns = ['id', 'job_name', 'salary', 'company_name', 'company_url',
                      'location', 'experience', 'education', 'source', 'collection_time']

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logging.error(f"搜索岗位失败: {e}")
            return []

    def export_to_dict(self) -> Dict:
        """
        导出所有数据为字典格式

        Returns:
            dict: 包含所有数据的字典
        """
        try:
            # 获取所有企业
            self.cursor.execute("SELECT id, name, url FROM companies")
            companies = {}
            for row in self.cursor.fetchall():
                companies[row[0]] = {
                    'id': row[0],
                    'name': row[1],
                    'url': row[2]
                }

            # 获取所有岗位
            self.cursor.execute("""
                SELECT id, company_id, job_name, salary, location,
                       experience, education, source, collection_time
                FROM jobs
            """)
            jobs = []
            for row in self.cursor.fetchall():
                jobs.append({
                    'id': row[0],
                    'company_id': row[1],
                    'job_name': row[2],
                    'salary': row[3],
                    'location': row[4],
                    'experience': row[5],
                    'education': row[6],
                    'source': row[7],
                    'collection_time': row[8],
                    'company_name': companies[row[1]]['name'],
                    'company_url': companies[row[1]]['url']
                })

            return {
                'companies': list(companies.values()),
                'jobs': jobs
            }

        except Exception as e:
            logging.error(f"导出数据失败: {e}")
            return {'companies': [], 'jobs': []}

    def add_is_imported_column(self):
        """
        为现有的 companies 表添加 is_imported 列
        用于数据库升级
        """
        try:
            # 检查列是否已存在
            self.cursor.execute("PRAGMA table_info(companies)")
            columns = [col[1] for col in self.cursor.fetchall()]

            if 'is_imported' not in columns:
                self.cursor.execute("""
                    ALTER TABLE companies ADD COLUMN is_imported BOOLEAN DEFAULT 0
                """)
                self.conn.commit()
                logging.info("已添加 is_imported 列到 companies 表")
                return True
            else:
                logging.info("is_imported 列已存在，无需添加")
                return True

        except Exception as e:
            logging.error(f"添加 is_imported 列失败: {e}")
            return False

    def add_platform_column(self):
        """
        为现有的 jobs 表添加 platform 列
        用于数据库升级
        """
        try:
            # 检查列是否已存在
            self.cursor.execute("PRAGMA table_info(jobs)")
            columns = [col[1] for col in self.cursor.fetchall()]

            if 'platform' not in columns:
                self.cursor.execute("""
                    ALTER TABLE jobs ADD COLUMN platform TEXT
                """)
                self.conn.commit()
                logging.info("已添加 platform 列到 jobs 表")
                return True
            else:
                logging.info("platform 列已存在，无需添加")
                return True

        except Exception as e:
            logging.error(f"添加 platform 列失败: {e}")
            return False

    def add_discarded_column(self):
        """
        为现有的 companies 表添加 is_discarded 列
        用于数据库升级
        """
        try:
            # 检查列是否已存在
            self.cursor.execute("PRAGMA table_info(companies)")
            columns = [col[1] for col in self.cursor.fetchall()]

            if 'is_discarded' not in columns:
                self.cursor.execute("""
                    ALTER TABLE companies ADD COLUMN is_discarded BOOLEAN DEFAULT 0
                """)
                self.conn.commit()
                logging.info("已添加 is_discarded 列到 companies 表")
                return True
            else:
                logging.info("is_discarded 列已存在，无需添加")
                return True

        except Exception as e:
            logging.error(f"添加 is_discarded 列失败: {e}")
            return False

    def add_monitoring_time_columns(self):
        """
        为现有的 monitoring_configs 表添加时间范围列
        用于数据库升级
        """
        try:
            # 检查列是否已存在
            self.cursor.execute("PRAGMA table_info(monitoring_configs)")
            columns = [col[1] for col in self.cursor.fetchall()]

            columns_added = False

            if 'monitoring_start_time' not in columns:
                self.cursor.execute("""
                    ALTER TABLE monitoring_configs ADD COLUMN monitoring_start_time TEXT DEFAULT '09:00'
                """)
                columns_added = True
                logging.info("已添加 monitoring_start_time 列到 monitoring_configs 表")
            else:
                logging.info("monitoring_start_time 列已存在，无需添加")

            if 'monitoring_end_time' not in columns:
                self.cursor.execute("""
                    ALTER TABLE monitoring_configs ADD COLUMN monitoring_end_time TEXT DEFAULT '18:00'
                """)
                columns_added = True
                logging.info("已添加 monitoring_end_time 列到 monitoring_configs 表")
            else:
                logging.info("monitoring_end_time 列已存在，无需添加")

            if columns_added:
                self.conn.commit()

            return True

        except Exception as e:
            logging.error(f"添加监控时间列失败: {e}")
            return False

    def toggle_company_imported(self, company_id: int) -> Optional[bool]:
        """
        切换企业入库状态

        Args:
            company_id: 企业 ID

        Returns:
            bool: 新的入库状态，失败返回 None
        """
        try:
            # 获取当前状态
            self.cursor.execute("""
                SELECT is_imported FROM companies WHERE id = ?
            """, (company_id,))

            result = self.cursor.fetchone()
            if result is None:
                logging.warning(f"企业 ID {company_id} 不存在")
                return None

            current_status = result[0]
            new_status = 0 if current_status else 1

            # 更新状态
            self.cursor.execute("""
                UPDATE companies SET is_imported = ? WHERE id = ?
            """, (new_status, company_id))

            self.conn.commit()
            logging.info(f"企业 ID {company_id} 入库状态已切换为 {new_status}")
            return bool(new_status)

        except Exception as e:
            logging.error(f"切换企业入库状态失败: {e}")
            return None

    def toggle_company_discarded(self, company_id: int) -> Optional[bool]:
        """
        切换企业废弃状态

        未废弃 → 已废弃（同时取消已入库状态）
        已废弃 → 未废弃（恢复为未入库状态）

        Args:
            company_id: 企业 ID

        Returns:
            bool: 新的废弃状态，失败返回 None
        """
        try:
            # 获取当前状态
            self.cursor.execute("""
                SELECT is_discarded, is_imported FROM companies WHERE id = ?
            """, (company_id,))

            result = self.cursor.fetchone()
            if result is None:
                logging.warning(f"企业 ID {company_id} 不存在")
                return None

            current_discarded = result[0]
            current_imported = result[1]

            if current_discarded:
                # 当前已废弃 → 恢复为未废弃
                new_discarded = 0
                new_imported = 0  # 恢复为未入库状态
            else:
                # 当前未废弃 → 标记为已废弃
                new_discarded = 1
                new_imported = 0  # 取消已入库状态

            # 更新状态
            self.cursor.execute("""
                UPDATE companies
                SET is_discarded = ?, is_imported = ?
                WHERE id = ?
            """, (new_discarded, new_imported, company_id))

            self.conn.commit()
            logging.info(f"企业 ID {company_id} 废弃状态已切换为 {new_discarded}")
            return bool(new_discarded)

        except Exception as e:
            logging.error(f"切换企业废弃状态失败: {e}")
            return None

    def batch_import_companies(self, company_ids: List[int]) -> int:
        """
        批量标记企业为已入库

        Args:
            company_ids: 企业 ID 列表

        Returns:
            int: 成功更新的企业数量
        """
        if not company_ids:
            return 0

        try:
            # 使用事务批量更新
            placeholders = ','.join(['?' for _ in company_ids])
            query = f"""
                UPDATE companies
                SET is_imported = 1
                WHERE id IN ({placeholders})
            """

            self.cursor.execute(query, company_ids)
            self.conn.commit()

            updated_count = self.cursor.rowcount
            logging.info(f"批量更新 {updated_count} 家企业为已入库")
            return updated_count

        except Exception as e:
            logging.error(f"批量更新企业状态失败: {e}")
            self.conn.rollback()
            return 0

    def get_companies_with_import_status(self, filter_type: str = 'all') -> List[Dict]:
        """
        获取企业列表，支持按入库状态筛选
        只返回有 URL 的企业

        Args:
            filter_type: 筛选类型 'all' | 'imported' | 'unimported'

        Returns:
            list: 企业信息列表
        """
        try:
            query = """
                SELECT
                    c.id,
                    c.name,
                    c.url,
                    c.is_imported,
                    c.is_discarded,
                    COUNT(j.id) as job_count,
                    GROUP_CONCAT(DISTINCT j.location) as locations,
                    GROUP_CONCAT(DISTINCT j.platform) as platforms
                FROM companies c
                LEFT JOIN jobs j ON c.id = j.company_id
                WHERE c.url IS NOT NULL AND c.url != ''
            """

            # 添加筛选条件
            if filter_type == 'imported':
                query += " AND c.is_imported = 1 AND c.is_discarded = 0"
            elif filter_type == 'unimported':
                query += " AND c.is_imported = 0 AND c.is_discarded = 0"
            elif filter_type == 'discarded':
                query += " AND c.is_discarded = 1"
            elif filter_type == 'undiscarded':
                query += " AND c.is_discarded = 0"

            query += " GROUP BY c.id, c.name, c.url, c.is_imported, c.is_discarded ORDER BY c.id DESC"

            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            columns = ['id', 'name', 'url', 'is_imported', 'is_discarded', 'job_count', 'locations', 'platforms']

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logging.error(f"获取企业列表失败: {e}")
            return []

    def get_all_jobs(self) -> List[Dict]:
        """
        获取所有岗位信息

        Returns:
            list: 岗位信息列表
        """
        try:
            query = """
                SELECT
                    j.id,
                    j.job_name,
                    j.salary,
                    c.name as company_name,
                    j.location,
                    j.experience,
                    j.education,
                    j.platform,
                    j.collection_time
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                ORDER BY j.id DESC
            """

            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            columns = ['id', 'job_name', 'salary', 'company_name', 'location',
                      'experience', 'education', 'platform', 'collection_time']

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logging.error(f"获取岗位列表失败: {e}")
            return []

    # ==================== Monitoring Database Methods ====================

    def init_monitoring_tables(self):
        """
        Initialize monitoring-related tables
        """
        try:
            # Create riskbird_config table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS riskbird_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT NOT NULL UNIQUE,
                    config_value TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT DEFAULT 'system'
                )
            """)

            # Create monitoring_configs table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_name TEXT NOT NULL,
                    region_codes TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    interval_minutes INTEGER DEFAULT 5,
                    reg_cap TEXT,
                    monitoring_start_time TEXT DEFAULT '09:00',
                    monitoring_end_time TEXT DEFAULT '18:00',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create monitored_companies table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitored_companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id INTEGER,
                    company_name TEXT NOT NULL,
                    credit_code TEXT UNIQUE,
                    reg_date TEXT,
                    reg_cap TEXT,
                    region_code TEXT,
                    region_name TEXT,
                    legal_representative TEXT,
                    contact TEXT,
                    address TEXT,
                    business_scope TEXT,
                    monitoring_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'riskbird',
                    is_processed BOOLEAN DEFAULT 0,
                    notes TEXT,
                    FOREIGN KEY (config_id) REFERENCES monitoring_configs (id)
                )
            """)

            # Create indexes
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_company_name
                ON monitored_companies(company_name)
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_monitoring_time
                ON monitored_companies(monitoring_time)
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_config_time
                ON monitored_companies(config_id, monitoring_time)
            """)

            self.cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_credit_code
                ON monitored_companies(credit_code)
            """)

            self.conn.commit()
            logging.info("Monitoring tables initialized successfully")
            return True

        except Exception as e:
            logging.error(f"Failed to initialize monitoring tables: {e}")
            return False

    def insert_riskbird_config(self, config_key: str, config_value: str) -> bool:
        """
        Insert or update riskbird config

        Args:
            config_key: Configuration key
            config_value: Configuration value

        Returns:
            bool: Success status
        """
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO riskbird_config (config_key, config_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (config_key, config_value))
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to insert riskbird config: {e}")
            return False

    def get_riskbird_config(self, config_key: str) -> Optional[str]:
        """
        Get riskbird config value

        Args:
            config_key: Configuration key

        Returns:
            str: Configuration value or None
        """
        try:
            self.cursor.execute("""
                SELECT config_value FROM riskbird_config
                WHERE config_key = ? AND is_active = 1
            """, (config_key,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logging.error(f"Failed to get riskbird config: {e}")
            return None

    def get_all_riskbird_configs(self) -> Dict[str, str]:
        """
        Get all active riskbird configs

        Returns:
            dict: All config key-value pairs
        """
        try:
            self.cursor.execute("""
                SELECT config_key, config_value FROM riskbird_config
                WHERE is_active = 1
            """)
            return {row[0]: row[1] for row in self.cursor.fetchall()}
        except Exception as e:
            logging.error(f"Failed to get all riskbird configs: {e}")
            return {}

    def update_riskbird_config(self, config_key: str, config_value: str) -> bool:
        """
        Update riskbird config

        Args:
            config_key: Configuration key
            config_value: New configuration value

        Returns:
            bool: Success status
        """
        try:
            self.cursor.execute("""
                UPDATE riskbird_config
                SET config_value = ?, updated_at = CURRENT_TIMESTAMP
                WHERE config_key = ?
            """, (config_value, config_key))
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to update riskbird config: {e}")
            return False

    def insert_monitoring_config(self, config_name: str, region_codes: str,
                                 interval_minutes: int = 5, reg_cap: str = None,
                                 monitoring_start_time: str = '09:00',
                                 monitoring_end_time: str = '18:00') -> Optional[int]:
        """
        Insert monitoring config

        Args:
            config_name: Configuration name
            region_codes: Region codes JSON string
            interval_minutes: Monitoring interval in minutes
            reg_cap: Registered capital filter (optional)
            monitoring_start_time: Monitoring start time (default '09:00')
            monitoring_end_time: Monitoring end time (default '18:00')

        Returns:
            int: Config ID or None
        """
        try:
            # Check connection before insert
            if not self.conn or not self.cursor:
                logging.error("Database connection is not established")
                return None

            self.cursor.execute("""
                INSERT INTO monitoring_configs
                (config_name, region_codes, interval_minutes, reg_cap, monitoring_start_time, monitoring_end_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (config_name, region_codes, interval_minutes, reg_cap, monitoring_start_time, monitoring_end_time))
            self.conn.commit()

            return self.cursor.lastrowid
        except Exception as e:
            logging.error(f"Failed to insert monitoring config: {e}", exc_info=True)
            return None

    def get_all_monitoring_configs(self) -> List[Dict]:
        """
        Get all monitoring configs

        Returns:
            list: List of config dicts
        """
        try:
            self.cursor.execute("""
                SELECT id, config_name, region_codes, is_active,
                       interval_minutes, reg_cap, monitoring_start_time, monitoring_end_time,
                       created_at, updated_at
                FROM monitoring_configs
                ORDER BY id DESC
            """)
            rows = self.cursor.fetchall()
            columns = ['id', 'config_name', 'region_codes', 'is_active',
                      'interval_minutes', 'reg_cap', 'monitoring_start_time', 'monitoring_end_time',
                      'created_at', 'updated_at']
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Failed to get monitoring configs: {e}")
            return []

    def get_monitoring_config(self, config_id: int) -> Optional[Dict]:
        """
        Get specific monitoring config

        Args:
            config_id: Configuration ID

        Returns:
            dict: Config data or None
        """
        try:
            self.cursor.execute("""
                SELECT id, config_name, region_codes, is_active,
                       interval_minutes, reg_cap, monitoring_start_time, monitoring_end_time,
                       created_at, updated_at
                FROM monitoring_configs
                WHERE id = ?
            """, (config_id,))
            row = self.cursor.fetchone()
            if row:
                columns = ['id', 'config_name', 'region_codes', 'is_active',
                          'interval_minutes', 'reg_cap', 'monitoring_start_time', 'monitoring_end_time',
                          'created_at', 'updated_at']
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logging.error(f"Failed to get monitoring config: {e}")
            return None

    def update_monitoring_config(self, config_id: int, **kwargs) -> bool:
        """
        Update monitoring config

        Args:
            config_id: Configuration ID
            **kwargs: Fields to update

        Returns:
            bool: Success status
        """
        # Validate column names
        ALLOWED_COLUMNS = {'config_name', 'region_codes', 'is_active', 'interval_minutes', 'reg_cap',
                          'monitoring_start_time', 'monitoring_end_time'}
        invalid_columns = set(kwargs.keys()) - ALLOWED_COLUMNS
        if invalid_columns:
            logging.error(f"Invalid columns: {invalid_columns}")
            return False

        try:
            if not kwargs:
                return False

            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [config_id]

            self.cursor.execute(f"""
                UPDATE monitoring_configs
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to update monitoring config: {e}")
            return False

    def delete_monitoring_config(self, config_id: int) -> bool:
        """
        Delete monitoring config and all associated data

        Args:
            config_id: Configuration ID

        Returns:
            bool: Success status
        """
        try:
            # Check if config exists
            self.cursor.execute("SELECT id FROM monitoring_configs WHERE id = ?", (config_id,))
            if not self.cursor.fetchone():
                logging.warning(f"Config {config_id} does not exist, already deleted")
                return True  # Already deleted is considered success

            # Delete in correct order due to foreign key constraints:
            # 1. monitoring_runs (execution history)
            # 2. monitored_companies (company data)
            # 3. monitoring_configs (configuration)

            self.cursor.execute("DELETE FROM monitoring_runs WHERE config_id = ?", (config_id,))
            rows_companies = self.cursor.execute("DELETE FROM monitored_companies WHERE config_id = ?", (config_id,))
            rows_configs = self.cursor.execute("DELETE FROM monitoring_configs WHERE id = ?", (config_id,))

            self.conn.commit()
            logging.info(f"Deleted monitoring config {config_id} and all associated data ({rows_companies} companies, {rows_configs} configs)")
            return True
        except Exception as e:
            logging.error(f"Failed to delete monitoring config: {e}")
            return False

    def insert_monitored_company(self, company_data: Dict) -> Optional[int]:
        """
        Insert monitored company with duplicate check

        Args:
            company_data: Company data dict

        Returns:
            int: Company ID or None (if duplicate)
        """
        try:
            self.cursor.execute("""
                INSERT INTO monitored_companies
                (config_id, company_name, credit_code, reg_date, reg_cap,
                 region_code, region_name, legal_representative, contact,
                 address, business_scope)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_data.get('config_id'),
                company_data.get('company_name'),
                company_data.get('credit_code'),
                company_data.get('reg_date'),
                company_data.get('reg_cap'),
                company_data.get('region_code'),
                company_data.get('region_name'),
                company_data.get('legal_representative'),
                company_data.get('contact'),
                company_data.get('address'),
                company_data.get('business_scope')
            ))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            # Duplicate credit_code
            logging.debug(f"Duplicate company: {company_data.get('credit_code')}")
            return None
        except Exception as e:
            logging.error(f"Failed to insert monitored company: {e}")
            return None

    def get_monitored_companies(self, config_id: int = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get monitored companies with date filtering and config name

        Args:
            config_id: Filter by config ID (optional)
            start_date: Filter by start date (YYYY-MM-DD format)
            end_date: Filter by end date (YYYY-MM-DD format)
            limit: Number of records to return
            offset: Pagination offset

        Returns:
            List[Dict]: List of monitored companies with config_name
        """
        try:
            query = """
                SELECT
                    mc.id,
                    mc.config_id,
                    mc2.config_name,
                    mc.company_name,
                    mc.credit_code,
                    mc.reg_date,
                    mc.reg_cap,
                    mc.region_code,
                    mc.region_name,
                    mc.legal_representative,
                    mc.contact,
                    mc.address,
                    mc.business_scope,
                    mc.monitoring_time,
                    mc.source,
                    mc.is_processed,
                    mc.notes
                FROM monitored_companies mc
                LEFT JOIN monitoring_configs mc2 ON mc.config_id = mc2.id
                WHERE 1=1
            """
            params = []

            if config_id:
                query += " AND mc.config_id = ?"
                params.append(config_id)

            # Add date filtering
            if start_date:
                query += " AND DATE(mc.monitoring_time) >= ?"
                params.append(start_date)

            if end_date:
                query += " AND DATE(mc.monitoring_time) <= ?"
                params.append(end_date)

            query += " ORDER BY mc.monitoring_time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            columns = ['id', 'config_id', 'config_name', 'company_name', 'credit_code',
                      'reg_date', 'reg_cap', 'region_code', 'region_name',
                      'legal_representative', 'contact', 'address', 'business_scope',
                      'monitoring_time', 'source', 'is_processed', 'notes']
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Failed to get monitored companies: {e}")
            return []

    def get_monitoring_stats(self) -> Dict:
        """
        Get monitoring statistics

        Returns:
            dict: Statistics
        """
        try:
            stats = {}

            # Total companies monitored
            self.cursor.execute("SELECT COUNT(*) FROM monitored_companies")
            stats['total_companies'] = self.cursor.fetchone()[0]

            # Today's additions
            self.cursor.execute("""
                SELECT COUNT(*) FROM monitored_companies
                WHERE DATE(monitoring_time) = DATE('now')
            """)
            stats['today_added'] = self.cursor.fetchone()[0]

            # Active configs
            self.cursor.execute("""
                SELECT COUNT(*) FROM monitoring_configs WHERE is_active = 1
            """)
            stats['active_configs'] = self.cursor.fetchone()[0]

            # Unprocessed companies
            self.cursor.execute("""
                SELECT COUNT(*) FROM monitored_companies WHERE is_processed = 0
            """)
            stats['unprocessed'] = self.cursor.fetchone()[0]

            return stats
        except Exception as e:
            logging.error(f"Failed to get monitoring stats: {e}")
            return {}

    def insert_monitoring_run(self, config_id: int, config_name: str,
                             success: bool, companies_added: int = 0,
                             companies_skipped: int = 0,
                             error_message: str = None) -> Optional[int]:
        """
        Insert a monitoring run record

        Args:
            config_id: Configuration ID
            config_name: Configuration name
            success: Whether the run was successful
            companies_added: Number of companies added
            companies_skipped: Number of companies skipped
            error_message: Error message if failed

        Returns:
            int: Inserted record ID or None if failed
        """
        try:
            # Get current Beijing time
            beijing_tz = ZoneInfo("Asia/Shanghai")
            run_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')

            self.cursor.execute("""
                INSERT INTO monitoring_runs
                (config_id, config_name, run_time, success, companies_added, companies_skipped, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (config_id, config_name, run_time, success, companies_added,
                  companies_skipped, error_message))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logging.error(f"Failed to insert monitoring run: {e}")
            return None

    def get_monitoring_runs(self, config_id: Optional[int] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           limit: int = 50, offset: int = 0) -> list:
        """
        Get monitoring run records with date filtering

        Args:
            config_id: Filter by config ID (optional)
            start_date: Filter by start date (YYYY-MM-DD format)
            end_date: Filter by end date (YYYY-MM-DD format)
            limit: Number of records to return
            offset: Pagination offset

        Returns:
            list: List of run records
        """
        try:
            query = """
                SELECT id, config_id, config_name, run_time, success,
                       companies_added, companies_skipped, error_message
                FROM monitoring_runs
                WHERE 1=1
            """
            params = []

            if config_id:
                query += " AND config_id = ?"
                params.append(config_id)

            # Add date filtering
            if start_date:
                query += " AND DATE(run_time) >= ?"
                params.append(start_date)

            if end_date:
                query += " AND DATE(run_time) <= ?"
                params.append(end_date)

            query += " ORDER BY run_time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            columns = ['id', 'config_id', 'config_name', 'run_time',
                      'success', 'companies_added', 'companies_skipped', 'error_message']
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Failed to get monitoring runs: {e}")
            return []

    def get_monitoring_runs_count(self) -> int:
        """
        Get total count of monitoring runs

        Returns:
            int: Total count
        """
        try:
            self.cursor.execute("SELECT COUNT(*) FROM monitoring_runs")
            return self.cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"Failed to get monitoring runs count: {e}")
            return 0


def main():
    """测试数据库功能"""
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s [%(levelname)s] %(message)s')

    # 创建数据库实例
    db = BOSSDatabase()

    # 连接数据库
    if not db.connect():
        return

    # 初始化表
    if not db.init_tables():
        db.close()
        return

    # 测试插入数据
    print("\n测试插入数据...")

    # 插入企业
    company_id = db.insert_company("测试公司", "https://www.example.com")
    print(f"插入企业 ID: {company_id}")

    # 插入岗位
    job_data = {
        'job_name': 'Python 工程师',
        'salary': '20-35K',
        'location': '上海',
        'experience': '3-5年',
        'education': '本科',
        'source': '测试',
        'collection_time': '2026-03-12 15:00'
    }
    db.insert_job(company_id, job_data)
    print("插入岗位成功")

    # 查询统计
    print("\n统计信息:")
    stats = db.get_total_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 查询岗位
    print("\n查询岗位:")
    jobs = db.search_jobs(limit=5)
    for job in jobs:
        print(f"  {job['job_name']} - {job['company_name']}")

    # 关闭数据库
    db.close()


if __name__ == '__main__':
    main()
