"""
BOSS 直聘职位信息解析器
"""

import re
from typing import List, Dict
from bs4 import BeautifulSoup

from .base import BaseParser


class BossZhipinParser(BaseParser):
    """BOSS 直聘解析器"""

    SITE_CODE = 'boss_zhipin'
    SITE_NAME = 'BOSS直聘'

    def parse(self, html: str, source: str = None) -> List[Dict]:
        """
        解析 BOSS 直聘 HTML 内容

        Args:
            html: HTML 源码
            source: 数据来源标识

        Returns:
            职位信息列表
        """
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []

        # 查找所有岗位卡片
        cards = soup.find_all('li', class_='job-card-box')

        for card in cards:
            try:
                # 提取岗位名称
                job_name_tag = card.find('a', class_='job-name')
                job_name = job_name_tag.get_text(strip=True) if job_name_tag else ''

                # 提取薪资
                salary_tag = card.find('span', class_='job-salary')
                salary = self.clean_salary(
                    salary_tag.get_text(strip=True) if salary_tag else ''
                )

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
                    }
                    jobs.append(job)

            except Exception as e:
                print(f"BOSS直聘解析出错: {e}")
                continue

        # 去重
        jobs = self.deduplicate(jobs)

        # 添加来源标识
        jobs = self.add_source(jobs, source)

        return jobs

    def clean_salary(self, salary: str) -> str:
        """
        清理薪资中的特殊字符，将 BOSS 直聘的数字字体图标转换为正常数字

        Args:
            salary: 原始薪资字符串

        Returns:
            清理后的薪资字符串
        """
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
