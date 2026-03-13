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
            logging.info(f"数据库连接成功: {self.db_path}")
            return True
        except Exception as e:
            logging.error(f"数据库连接失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logging.info("数据库连接已关闭")

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
                    COUNT(j.id) as job_count,
                    GROUP_CONCAT(DISTINCT j.location) as locations,
                    GROUP_CONCAT(DISTINCT j.platform) as platforms
                FROM companies c
                LEFT JOIN jobs j ON c.id = j.company_id
                WHERE c.url IS NOT NULL AND c.url != ''
            """

            # 添加筛选条件
            if filter_type == 'imported':
                query += " AND c.is_imported = 1"
            elif filter_type == 'unimported':
                query += " AND c.is_imported = 0"

            query += " GROUP BY c.id, c.name, c.url, c.is_imported ORDER BY c.id DESC"

            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            columns = ['id', 'name', 'url', 'is_imported', 'job_count', 'locations', 'platforms']

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
