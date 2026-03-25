"""
职位信息解析器模块
支持多个招聘网站
"""

from .base import BaseParser
from .boss_zhipin import BossZhipinParser
from .fiftyone_job import FiftyOneJobParser

# 解析器注册表
PARSERS = {
    'boss_zhipin': BossZhipinParser,
    '51job': FiftyOneJobParser,
}

# 支持的站点列表
SUPPORTED_SITES = [
    {'code': 'boss_zhipin', 'name': 'BOSS直聘', 'enabled': True},
    {'code': '51job', 'name': '前程无忧', 'enabled': True},
    {'code': 'zhaopin', 'name': '智联招聘', 'enabled': False},
    {'code': 'liepin', 'name': '猎聘', 'enabled': False},
]


def get_parser(site_code: str):
    """
    获取指定站点的解析器

    Args:
        site_code: 站点代码

    Returns:
        解析器实例
    """
    parser_class = PARSERS.get(site_code)
    if not parser_class:
        raise ValueError(f"不支持的站点: {site_code}")

    return parser_class()


def get_supported_sites():
    """
    获取支持的站点列表

    Returns:
        list: 站点列表
    """
    return SUPPORTED_SITES
