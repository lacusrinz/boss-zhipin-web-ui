"""
前程无忧(51job)职位信息解析器
"""

import re
from typing import List, Dict
from bs4 import BeautifulSoup

from .base import BaseParser


class FiftyOneJobParser(BaseParser):
    """前程无忧(51job)解析器"""

    SITE_CODE = '51job'
    SITE_NAME = '前程无忧'

    @classmethod
    def detect(cls, html: str) -> bool:
        """
        检测 HTML 是否来自前程无忧(51job)

        Args:
            html: HTML 源码

        Returns:
            bool: 如果是前程无忧返回 True
        """
        # 51job 的典型特征
        indicators = [
            'joblist-item',          # 职位列表项的 class
            '51job.com',              # 域名
            '51jobcdn.com',           # CDN 域名
            'joblist-item-jobname',   # 职位名称 class
            'jobs.51job.com',         # 完整域名
            'jname',                  # 职位名称简写
        ]

        html_lower = html.lower()
        return any(indicator in html_lower for indicator in indicators)

    def parse(self, html: str, source: str = None) -> List[Dict]:
        """
        解析前程无忧 HTML 内容

        Args:
            html: HTML 源码
            source: 数据来源标识

        Returns:
            职位信息列表
        """
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []

        # 查找所有岗位卡片
        cards = soup.find_all('div', class_='joblist-item')

        for card in cards:
            try:
                # 提取岗位名称
                job_name = ''
                job_name_tag = card.find('span', class_='jname')
                if job_name_tag:
                    # 优先使用 title 属性，否则使用文本
                    job_name = job_name_tag.get('title', '') or job_name_tag.get_text(strip=True)

                # 提取薪资
                salary_tag = card.find('span', class_='sal')
                salary = salary_tag.get_text(strip=True) if salary_tag else ''

                # 提取地点
                location = ''
                area_div = card.find('div', class_='area')
                if area_div:
                    shrink_div = area_div.find('div', class_='shrink-0')
                    if shrink_div:
                        location = shrink_div.get_text(strip=True)

                # 提取公司名称
                company = ''
                company_name_tag = card.find('span', class_='cname')
                if company_name_tag:
                    # 优先使用 title 属性，否则使用文本
                    company = company_name_tag.get('title', '') or company_name_tag.get_text(strip=True)

                # 提取公司 URL
                company_url = ''
                company_link = card.find('a', class_='comp')
                if company_link and company_link.get('href'):
                    href = company_link.get('href')
                    if href and not href.startswith('javascript:'):
                        company_url = href

                # 51job HTML 中没有直接显示经验和学历信息
                # 这些信息在 sensorsdata JSON 属性中，但纯 HTML 解析无法获取
                experience = ''
                education = ''

                if job_name:
                    job = {
                        'job_name': job_name,
                        'salary': salary,
                        'company': company,
                        'company_url': company_url,
                        'location': location,
                        'experience': experience,
                        'education': education,
                    }
                    jobs.append(job)

            except Exception as e:
                print(f"前程无忧解析出错: {e}")
                continue

        # 去重
        jobs = self.deduplicate(jobs)

        # 添加平台标识
        jobs = self.add_platform(jobs)

        # 添加 source 标识
        for job in jobs:
            job['source'] = source or ''

        return jobs

    def clean_salary(self, salary: str) -> str:
        """
        清理薪资字符串

        Args:
            salary: 原始薪资字符串

        Returns:
            清理后的薪资字符串
        """
        if not salary:
            return ''

        # 51job 的薪资格式相对规范，直接去除多余空格即可
        return salary.strip()
