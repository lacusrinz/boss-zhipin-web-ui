#!/usr/bin/env python3
"""
显示监控任务最后一次执行的详细请求体和返回内容
"""
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from riskbird_search import build_search_params, call_riskbird_search_api
from database import BOSSDatabase
from token_service import TokenService


def show_last_execution():
    """显示最后一次执行的详细信息"""
    print("=" * 80)
    print("监控任务最后一次执行详情")
    print("=" * 80)
    print()

    # Connect to database
    db_path = Path(__file__).parent.parent / "data" / "boss_jobs.db"
    db = BOSSDatabase(str(db_path))

    if not db.connect():
        print("❌ 无法连接到数据库")
        return

    # Get last run record
    db.cursor.execute("""
        SELECT config_id, config_name, run_time, success, companies_added, error_message
        FROM monitoring_runs
        ORDER BY run_time DESC
        LIMIT 1
    """)
    last_run = db.cursor.fetchone()

    if not last_run:
        print("❌ 没有找到执行记录")
        db.close()
        return

    config_id, config_name, run_time, success, companies_added, error_message = last_run

    print(f"📅 执行时间: {run_time}")
    print(f"📝 配置名称: {config_name}")
    print(f"🆔 配置ID: {config_id}")
    print(f"✅ 执行状态: {'成功' if success else '失败'}")
    print(f"📊 新增企业: {companies_added}")
    if error_message:
        print(f"❌ 错误信息: {error_message}")
    print()

    # Get config details
    config = db.get_monitoring_config(config_id)
    if config:
        region_codes = json.loads(config['region_codes'])
        interval_minutes = config['interval_minutes']
        reg_cap = config.get('reg_cap', '')

        print("-" * 80)
        print("配置参数:")
        print(f"  监控地区: {len(region_codes)} 个")
        print(f"  地区代码: {', '.join(region_codes)}")
        print(f"  监控间隔: {interval_minutes} 分钟")
        print(f"  注册资本: {reg_cap or '无限制'}")
        print()

    # Get API credentials
    encrypted_token = db.get_riskbird_config('token')
    app_uuid = db.get_riskbird_config('app_uuid')

    if not encrypted_token or not app_uuid:
        print("⚠️  未配置 API 凭证，无法显示实际请求/响应")
        print()
        print("但可以显示模拟请求体:")
        print()

        # Show mock request body
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')

        search_params = build_search_params(
            regionid=','.join(region_codes[:5]),  # API限制5个地区
            regcap=reg_cap,
            esdate=f'{today}￥{today}',
            status='1'
        )

        print("📤 模拟请求体 (前5个地区):")
        print("-" * 80)
        print(json.dumps(json.loads(search_params['aoData']), ensure_ascii=False, indent=2))
        print()

        db.close()
        return

    # Decrypt token
    token_service = TokenService()
    try:
        token = token_service.decrypt(encrypted_token)
    except Exception as e:
        print(f"❌ Token 解密失败: {e}")
        db.close()
        return

    print("=" * 80)
    print("实际 API 调用详情")
    print("=" * 80)
    print()

    # Show actual API calls
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    es_date = f'{today}￥{today}'

    # Split into batches (API limit: 5 regions per request)
    MAX_REGIONS_PER_REQUEST = 5
    region_batches = []
    for i in range(0, len(region_codes), MAX_REGIONS_PER_REQUEST):
        batch = region_codes[i:i + MAX_REGIONS_PER_REQUEST]
        region_batches.append(batch)

    print(f"📋 总共 {len(region_codes)} 个地区，分 {len(region_batches)} 批查询")
    print()

    # Simulate each batch
    for batch_idx, batch_regions in enumerate(region_batches, 1):
        regions_str = ','.join(batch_regions)

        print("=" * 80)
        print(f"批次 {batch_idx}/{len(region_batches)}: 地区代码 = {regions_str}")
        print("=" * 80)

        # Build search params
        search_params = build_search_params(
            regionid=regions_str,
            regcap=reg_cap,
            esdate=es_date,
            status='1'
        )

        # Parse aoData to show actual request
        ao_data = json.loads(search_params['aoData'])
        search_condition = None
        for item in ao_data:
            if item['name'] == 'cSearch_conditionData':
                search_condition = item['value']
                break

        print()
        print("📤 请求体:")
        print("-" * 80)
        print("URL: https://www.riskbird.com/riskbird-api/advance/search")
        print()
        print("搜索条件:")
        if search_condition:
            print(json.dumps(search_condition, ensure_ascii=False, indent=2))
        print()

        # Call actual API
        print("📥 API 响应:")
        print("-" * 80)

        try:
            api_response = call_riskbird_search_api(token, app_uuid, search_params)

            if 'error' in api_response:
                print(f"❌ API 调用失败")
                print(f"   错误类型: {api_response['error']}")
                print(f"   错误信息: {api_response.get('message', 'N/A')}")
                if api_response.get('status_code'):
                    print(f"   HTTP 状态码: {api_response['status_code']}")
            else:
                print("✅ API 调用成功")
                print()

                # Parse response
                data = api_response.get('data', [])
                if isinstance(data, dict):
                    total = data.get('iTotalRecords', 0)
                    companies = data.get('aaData', [])
                    print(f"📊 查询结果:")
                    print(f"   总记录数: {total}")
                    print(f"   本次返回: {len(companies)} 条")
                    print()

                    # Show first company as example
                    if companies:
                        print("📄 示例企业 (第1条):")
                        company = companies[0]
                        print(f"   企业名称: {company.get('name', 'N/A')}")
                        print(f"   统一社会信用代码: {company.get('creditNo', 'N/A')}")
                        print(f"   成立日期: {company.get('esDate', 'N/A')}")
                        print(f"   注册资本: {company.get('regCap', 'N/A')}")
                        print(f"   法定代表人: {company.get('frname', 'N/A')}")
                        print(f"   联系方式: {company.get('contact', 'N/A')}")
                        print()

                    # Show raw response (truncated)
                    print("📋 原始响应数据 (前500字符):")
                    response_str = json.dumps(api_response, ensure_ascii=False)
                    print(response_str[:500] + "..." if len(response_str) > 500 else response_str)

        except Exception as e:
            print(f"❌ API 调用异常: {e}")

        print()

    db.close()
    print("=" * 80)
    print("详情显示完成")
    print("=" * 80)


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    show_last_execution()
