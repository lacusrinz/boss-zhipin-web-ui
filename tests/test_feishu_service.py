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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
