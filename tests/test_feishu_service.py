"""
FeishuService 单元测试
"""
import os
import pytest
from unittest.mock import patch, Mock
from code.feishu_service import FeishuService


class TestFeishuServiceToken:
    """测试 Token 管理功能"""

    @patch('code.feishu_service.requests.post')
    def test_get_tenant_access_token_success(self, mock_post):
        """测试成功获取 tenant_access_token"""
        # Mock API 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'tenant_access_token': 'test_token_123',
            'expire': 7200
        }
        mock_post.return_value = mock_response

        # 创建服务实例
        service = FeishuService('test_app_id', 'test_app_secret')

        # 调用方法
        token = service.get_tenant_access_token()

        # 验证
        assert token == 'test_token_123'
        mock_post.assert_called_once()

    @patch('code.feishu_service.requests.post')
    def test_get_tenant_access_token_cached(self, mock_post):
        """测试 Token 缓存功能"""
        # 第一次调用返回 token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'tenant_access_token': 'test_token_123',
            'expire': 7200
        }
        mock_post.return_value = mock_response

        service = FeishuService('test_app_id', 'test_app_secret')

        # 第一次获取
        token1 = service.get_tenant_access_token()
        # 第二次获取（应该使用缓存）
        token2 = service.get_tenant_access_token()

        # 验证只调用了一次 API
        assert token1 == token2 == 'test_token_123'
        assert mock_post.call_count == 1


class TestFeishuServiceMessageFormatting:
    """测试消息格式化功能"""

    def test_format_monitoring_notification_single_company(self):
        """测试单企业的消息格式化"""
        service = FeishuService('test_app_id', 'test_app_secret')

        companies = [
            {
                'company_name': '上海智能制造有限公司',
                'reg_cap': '500万',
                'monitoring_time': '2026-03-18 14:30:00'
            }
        ]

        message = service.format_monitoring_notification(companies, '华东地区监测')

        assert '华东地区监测' in message
        assert '上海智能制造有限公司' in message
        assert '500万' in message
        assert '1 家' in message

    def test_format_monitoring_notification_multiple_companies(self):
        """测试多企业的消息格式化"""
        service = FeishuService('test_app_id', 'test_app_secret')

        companies = [
            {
                'company_name': '上海智能制造有限公司',
                'reg_cap': '500万',
                'monitoring_time': '2026-03-18 14:30:00'
            },
            {
                'company_name': '苏州医疗器械科技有限公司',
                'reg_cap': '200万',
                'monitoring_time': '2026-03-18 14:30:00'
            }
        ]

        message = service.format_monitoring_notification(companies, '华东地区监测')

        assert '2 家' in message
        assert '1. 上海智能制造有限公司' in message
        assert '2. 苏州医疗器械科技有限公司' in message


class TestFeishuServiceSendMessage:
    """测试消息发送功能"""

    @patch('code.feishu_service.requests.post')
    def test_send_text_message_to_group(self, mock_post):
        """测试发送群聊消息"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'code': 0}
        mock_post.return_value = mock_response

        service = FeishuService('test_app_id', 'test_app_secret')
        service._token = 'test_token'  # 设置 mock token

        result = service.send_text_message(
            target_id='oc_test123',
            target_type='group',
            content='测试消息'
        )

        assert result.get('error') is None
        assert mock_post.call_count == 2  # 一次获取 token，一次发送消息

    @patch('code.feishu_service.requests.post')
    def test_send_text_message_api_error(self, mock_post):
        """测试 API 错误处理"""
        # Mock token 响应（成功）
        token_response = Mock()
        token_response.status_code = 200
        token_response.json.return_value = {
            'code': 0,
            'tenant_access_token': 'test_token',
            'expire': 7200
        }

        # Mock 消息发送响应（失败）
        message_response = Mock()
        message_response.status_code = 200
        message_response.json.return_value = {'code': 9999, 'msg': 'Invalid token'}

        mock_post.side_effect = [token_response, message_response]

        service = FeishuService('test_app_id', 'test_app_secret')

        result = service.send_text_message(
            target_id='oc_test123',
            target_type='group',
            content='测试消息'
        )

        assert 'error' in result
        assert result['error'] == 'Invalid token'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
