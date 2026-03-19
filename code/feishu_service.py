"""
飞书消息推送服务
处理飞书 API 交互，包括 Token 管理、消息发送等功能
"""
import os
import time
import json
import logging
import requests
from typing import Dict, List, Optional


class FeishuService:
    """飞书消息推送服务"""

    # API 端点
    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

    def __init__(self, app_id: str, app_secret: str, verify_ssl: Optional[bool] = None):
        """
        初始化飞书服务

        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用密钥
            verify_ssl: 是否验证 SSL 证书，None 则从环境变量读取
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: Optional[str] = None
        self._token_expire_time: Optional[float] = None
        self.logger = logging.getLogger(__name__)

        # SSL 证书验证：优先使用参数，否则从环境变量读取，默认 True
        if verify_ssl is None:
            self.verify_ssl = os.getenv('FEISHU_VERIFY_SSL', 'true').lower() == 'true'
        else:
            self.verify_ssl = verify_ssl

        if not self.verify_ssl:
            self.logger.warning("SSL 证书验证已禁用！这仅用于调试目的。")

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
            response = requests.post(
                self.TOKEN_URL,
                json=payload,
                timeout=10,
                verify=self.verify_ssl
            )
            response.raise_for_status()

            # 尝试解析 JSON，失败时记录详细错误
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                # 记录响应内容以便调试
                self.logger.error(f"JSON 解析失败: {e}")
                self.logger.error(f"响应状态码: {response.status_code}")
                self.logger.error(f"响应头: {dict(response.headers)}")
                self.logger.error(f"响应内容前500字符: {response.text[:500]}")
                raise Exception(f"飞书 API 返回非 JSON 响应，可能是网络或证书问题。详情: {str(e)}")

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

    def format_monitoring_notification(self, companies: List[Dict], config_name: str) -> str:
        """
        格式化监测结果为纯文本消息

        Args:
            companies: 企业列表
            config_name: 监测配置名称

        Returns:
            str: 格式化的纯文本消息
        """
        from datetime import datetime

        # 获取当前北京时间
        beijing_tz = datetime.now().strftime('%Y-%m-%d %H:%M')

        # 构建消息
        lines = [
            "🔔 企业监测新发现",
            "",
            f"监测配置: {config_name}",
            f"发现时间: {beijing_tz}",
            f"新增企业: {len(companies)} 家",
            "",
            "企业列表:"
        ]

        for idx, company in enumerate(companies, 1):
            company_name = company.get('company_name', '未知企业')
            reg_cap = company.get('reg_cap', '未知')
            lines.append(f"{idx}. {company_name} (注册资本: {reg_cap})")

        return "\n".join(lines)

    def send_text_message(self, target_id: str, target_type: str, content: str) -> Dict:
        """
        发送纯文本消息到群聊或个人

        Args:
            target_id: 目标 ID（群聊 ID 或用户 open_id）
            target_type: 目标类型 ('group' 或 'user')
            content: 消息内容

        Returns:
            dict: 结果字典
                  - 成功时: {'success': True}
                  - 失败时: {'error': 'error message'}
        """
        try:
            # 获取 access token
            token = self.get_tenant_access_token()

            # 设置 receive_id_type
            receive_id_type = "chat_id" if target_type == "group" else "open_id"

            # 构建请求头
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # 构建请求体
            payload = {
                "receive_id": target_id,
                "msg_type": "text",
                "content": json.dumps({"text": content})
            }

            # 添加 receive_id_type 到 URL 参数
            params = {"receive_id_type": receive_id_type}

            # 发送请求（带重试）
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        self.MESSAGE_URL,
                        headers=headers,
                        params=params,
                        json=payload,
                        timeout=10,
                        verify=self.verify_ssl  # 使用配置的 SSL 验证选项
                    )
                    response.raise_for_status()

                    # 尝试解析 JSON，失败时记录详细错误
                    try:
                        data = response.json()
                    except json.JSONDecodeError as e:
                        self.logger.error(f"JSON 解析失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                        self.logger.error(f"响应状态码: {response.status_code}")
                        self.logger.error(f"响应内容前500字符: {response.text[:500]}")
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            self.logger.warning(f"{wait_time}秒后重试...")
                            time.sleep(wait_time)
                            continue
                        else:
                            return {'error': f'飞书 API 返回非 JSON 响应: {str(e)}'}

                    if data.get('code') == 0:
                        self.logger.info(f"消息发送成功: {target_type}/{target_id}")
                        return {'success': True}
                    else:
                        error_msg = data.get('msg', 'Unknown error')
                        self.logger.error(f"飞书 API 返回错误: {error_msg}")
                        return {'error': error_msg}

                except requests.Timeout:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 指数退避
                        self.logger.warning(f"请求超时，{wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        return {'error': '请求超时'}

                except requests.RequestException as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        self.logger.warning(f"请求失败，{wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        return {'error': f'网络错误: {str(e)}'}

        except Exception as e:
            self.logger.error(f"发送消息异常: {e}")
            return {'error': str(e)}
