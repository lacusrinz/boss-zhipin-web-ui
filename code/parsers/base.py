"""
职位信息解析器基类
所有站点解析器必须继承此类并实现解析方法
"""

from abc import ABC, abstractmethod
from typing import List, Dict
from bs4 import BeautifulSoup


class BaseParser(ABC):
    """解析器基类"""

    # 站点信息
    SITE_CODE = None
    SITE_NAME = None

    def __init__(self):
        """初始化解析器"""
        if not self.SITE_CODE or not self.SITE_NAME:
            raise ValueError(f"{self.__class__.__name__} 必须定义 SITE_CODE 和 SITE_NAME")

    @abstractmethod
    def parse(self, html: str, source: str = None) -> List[Dict]:
        """
        解析 HTML 内容，提取职位信息

        Args:
            html: HTML 源码
            source: 数据来源标识（可选）

        Returns:
            职位信息列表，每个职位包含：
            {
                'job_name': str,
                'salary': str,
                'company': str,
                'company_url': str,
                'location': str,
                'experience': str,
                'education': str,
                'source': str  # 自动添加站点标识
            }
        """
        pass

    def clean_salary(self, salary: str) -> str:
        """
        清理薪资字符串（可选实现）

        Args:
            salary: 原始薪资字符串

        Returns:
            清理后的薪资字符串
        """
        return salary.strip() if salary else ''

    def deduplicate(self, jobs: List[Dict]) -> List[Dict]:
        """
        去重职位信息

        Args:
            jobs: 职位列表

        Returns:
            去重后的职位列表
        """
        seen = set()
        unique_jobs = []

        for job in jobs:
            key = f"{job.get('job_name')}_{job.get('company')}"
            if key not in seen and job.get('job_name'):
                seen.add(key)
                unique_jobs.append(job)

        return unique_jobs

    def add_source(self, jobs: List[Dict], source: str = None) -> List[Dict]:
        """
        为职位添加来源标识（已弃用，保留兼容性）
        平台信息现在使用 add_platform 方法

        Args:
            jobs: 职位列表
            source: 来源标识（如果为 None，使用站点代码）

        Returns:
            添加来源后的职位列表
        """
        if source is None:
            source = self.SITE_CODE

        for job in jobs:
            # source 字段用于存储查询关键字，不存储平台信息
            if 'source' not in job:
                job['source'] = ''

        return jobs

    def add_platform(self, jobs: List[Dict], platform: str = None) -> List[Dict]:
        """
        为职位添加平台标识

        Args:
            jobs: 职位列表
            platform: 平台标识（如果为 None，使用站点代码）

        Returns:
            添加平台后的职位列表
        """
        if platform is None:
            platform = self.SITE_CODE

        for job in jobs:
            job['platform'] = platform

        return jobs

    @classmethod
    def detect(cls, html: str) -> bool:
        """
        检测 HTML 是否属于此站点

        Args:
            html: HTML 源码

        Returns:
            bool: 如果是此站点的 HTML 返回 True，否则返回 False
        """
        return False

    @staticmethod
    def detect_site(html: str) -> str:
        """
        自动检测 HTML 来源站点

        Args:
            html: HTML 源码

        Returns:
            str: 站点代码，如果无法识别返回 'unknown'
        """
        from . import PARSERS

        for site_code, parser_class in PARSERS.items():
            if parser_class.detect(html):
                return site_code

        return 'unknown'
