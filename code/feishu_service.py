"""
飞书消息推送服务
处理飞书 API 交互，包括 Token 管理、消息发送等功能
"""
import os
import time
import logging
import requests
from typing import Dict, List, Optional


class FeishuService:
    """飞书消息推送服务"""

    # API 端点
    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

    def __init__(self, app_id: str, app_secret: str):
        """
        初始化飞书服务

        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用密钥
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: Optional[str] = None
        self._token_expire_time: Optional[float] = None
        self.logger = logging.getLogger(__name__)

    def get_tenant_access_token(self) -> str:
        """
        获取 tenant_access_token（支持自动刷新和缓存）

        Returns:
            str: tenant_access_token

        Raises:
            Exception: 获取 Token 失败时抛出异常
        """
        # 检查缓存是否有效（提前 5 分钟刷新）
        if self._token and self._token_expire_time:
            if time.time() < self._token_expire_time - 300:
                self.logger.debug("使用缓存的 tenant_access_token")
                return self._token

        # 请求新 Token
        self.logger.info("刷新 tenant_access_token")
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(self.TOKEN_URL, json=payload, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get('code') != 0:
                raise Exception(f"获取 Token 失败: {data.get('msg')}")

            self._token = data.get('tenant_access_token')
            expire = data.get('expire', 7200)  # 默认 2 小时
            self._token_expire_time = time.time() + expire

            self.logger.info("tenant_access_token 刷新成功")
            return self._token

        except requests.RequestException as e:
            self.logger.error(f"获取 Token 网络错误: {e}")
            raise Exception(f"获取 Token 失败: {str(e)}")
