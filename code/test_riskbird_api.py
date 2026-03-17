#!/usr/bin/env python3
"""
RiskBird API 测试脚本
用于调试监控任务的 API 连接问题
"""
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from riskbird_search import build_search_params, call_riskbird_search_api
from database import BOSSDatabase
from token_service import TokenService


def test_api_with_stored_credentials():
    """使用存储的凭证测试 API 连接"""
    print("=" * 60)
    print("RiskBird API 连接测试")
    print("=" * 60)
    print()

    # Connect to database
    db_path = Path(__file__).parent.parent / "data" / "boss_jobs.db"
    db = BOSSDatabase(str(db_path))

    if not db.connect():
        print("❌ 无法连接到数据库")
        return False

    # Get encrypted token from database
    encrypted_token = db.get_riskbird_config('token')
    app_uuid = db.get_riskbird_config('app_uuid')

    if not encrypted_token or not app_uuid:
        print("❌ 数据库中未找到 API 凭证")
        print("   请先在监控页面配置 Token 和 App UUID")
        db.close()
        return False

    # Decrypt token
    token_service = TokenService()
    try:
        token = token_service.decrypt(encrypted_token)
        print(f"✅ Token 解密成功")
        print(f"   App UUID: {app_uuid}")
        print(f"   Token (masked): {token_service.mask_token(token)}")
    except Exception as e:
        print(f"❌ Token 解密失败: {e}")
        db.close()
        return False

    print()
    print("-" * 60)
    print("开始测试 API 连接...")
    print("-" * 60)
    print()

    # Test 1: Minimal request
    print("测试 1: 最小请求（北京地区，今天）")
    test_params = build_search_params(
        regionid='110000',
        esdate='2026-03-17￥2026-03-17'
    )

    print(f"请求参数: {json.dumps(test_params, ensure_ascii=False, indent=2)}")
    print()

    response = call_riskbird_search_api(token, app_uuid, test_params)

    if 'error' in response:
        print(f"❌ API 调用失败")
        print(f"   错误类型: {response['error']}")
        print(f"   状态码: {response.get('status_code', 'N/A')}")
        print(f"   错误信息: {response.get('message', 'N/A')}")
        print()
        print("可能的原因:")
        if response.get('status_code') == 401:
            print("  - Token 已过期或无效")
            print("  - 请重新登录 RiskBird 获取新的 Token")
        elif response.get('status_code') == 500:
            print("  - RiskBird API 服务器内部错误")
            print("  - 可能是请求参数格式问题")
            print("  - 可能是 API 服务暂时不可用")
            print("  - 建议稍后重试或联系 RiskBird 支持")
        else:
            print("  - 网络连接问题")
            print("  - API 服务暂时不可用")
        db.close()
        return False
    else:
        print("✅ API 调用成功")
        print(f"   响应数据: {json.dumps(response, ensure_ascii=False, indent=2)[:500]}...")
        print()

    # Test 2: Request with capital filter
    print("-" * 60)
    print("测试 2: 带注册资本筛选的请求")
    test_params_2 = build_search_params(
        regionid='110000,310000',
        regcap='5000￥',
        esdate='2026-03-17￥2026-03-17'
    )

    response2 = call_riskbird_search_api(token, app_uuid, test_params_2)

    if 'error' in response2:
        print(f"❌ API 调用失败: {response2.get('message', 'Unknown error')}")
    else:
        print("✅ API 调用成功")
        if 'data' in response2:
            data = response2['data']
            if isinstance(data, dict):
                count = len(data.get('aaData', []))
            else:
                count = len(data) if isinstance(data, list) else 0
            print(f"   找到 {count} 家企业")

    db.close()
    return True


def test_manual_credentials():
    """使用手动输入的凭证测试"""
    print("=" * 60)
    print("RiskBird API 手动测试")
    print("=" * 60)
    print()

    token = input("请输入 Token: ").strip()
    app_uuid = input("请输入 App UUID: ").strip()

    if not token or not app_uuid:
        print("❌ Token 和 App UUID 不能为空")
        return False

    print()
    print("测试 API 连接...")

    test_params = build_search_params(
        regionid='110000',
        esdate='2026-03-17￥2026-03-17'
    )

    response = call_riskbird_search_api(token, app_uuid, test_params)

    if 'error' in response:
        print(f"❌ API 调用失败")
        print(f"   错误: {response}")
        return False
    else:
        print("✅ API 调用成功")
        print(f"   响应: {json.dumps(response, ensure_ascii=False, indent=2)[:500]}...")
        return True


if __name__ == "__main__":
    import logging

    # Enable detailed logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print()
    print("请选择测试模式:")
    print("[1] 使用存储的凭证测试（推荐）")
    print("[2] 手动输入凭证测试")
    print()

    choice = input("请选择 (1/2): ").strip()

    if choice == "1":
        success = test_api_with_stored_credentials()
    elif choice == "2":
        success = test_manual_credentials()
    else:
        print("无效的选择")
        success = False

    print()
    print("=" * 60)
    if success:
        print("✅ 测试完成")
    else:
        print("❌ 测试失败")
    print("=" * 60)
