#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RiskBird API 高级搜索接口访问脚本
创建时间: 2026-03-05
"""

import requests
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ==================== 配置区域 ====================

# 高级搜索 API
SEARCH_API_URL = "https://www.riskbird.com/riskbird-api/advance/search"
# 区域代码查询 API
REGION_API_URL = "https://www.riskbird.com/riskbird-api/advance/getRegionCodeMultiLevel"

# 请求头
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "App-Device": "WEB",
    "Origin": "https://www.riskbird.com",
    "Referer": "https://www.riskbird.com/senior/result",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Sec-Ch-Ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# Cookies
COOKIES = {
    "app-uuid": "WEB-B411E1DFB8B64B22B2DB261A43EE1653",
    "app-device": "WEB",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwYXNzd29yZCI6IjdjMjI0NmMzYjc2NTJhMzU4NWYwNzIyYmZlNWZkZDE5Iiwibmlja05hbWUiOiIxODY1MjQyMDQzNCIsIm1vYmlsZSI6IjQ0RDVFODA2NUU5NTM0MUE3RDNCNkVEODEyOTNBRTlFIiwiZXhwIjoxNzcyNjczMjYyLCJ1c2VySWQiOjI5NjUwMDksInV1aWQiOiI5NGE3YzE1Yi01OWVjLTQ3NTYtOWQ3ZS1iNjJjMjc0NDI2M2QiLCJ2ZXJzaW9uIjoidjYiLCJ1c2VybmFtZSI6IjE4NjUyNDIwNDM0In0.GKMjldFvo5nqyVXzUzcVusZh8-NErV3akg8MitYosGc",
    "userinfo": '%7B%22userId%22%3A2965009%2C%22inviteCode%22%3A%225592CADEADD73DE6%22%2C%22nickName%22%3A%2218652420434%22%2C%22unionid%22%3A%22oTZAV66jO1PW6bAq9NmVDSUHxdho%22%2C%22isVip%22%3Atrue%2C%22vipStatus%22%3A%22vip%22%2C%22vipEndTime%22%3A%222031-03-04%22%2C%22mobile%22%3A%2218652420434%22%2C%22email%22%3Anull%2C%22timestamp%22%3A1772671463061%2C%22userNewType%22%3Atrue%2C%22vipTimeOut%22%3A1825%2C%22isNoAdVip%22%3Afalse%2C%22notGetLoginVip%22%3Afalse%2C%22queryHistoryInfoDocSwitch%22%3A%221%22%2C%22vipExpireTime%22%3A1930406399000%2C%22currentDate%22%3A%222026-03-05%22%2C%22isQueryHistoryInfoDoc%22%3Afalse%2C%22isNoAdExpireDate%22%3Anull%2C%22isQueryRiskDoc%22%3Afalse%2C%22queryRiskDocSwitch%22%3A%221%22%2C%22status%22%3A%22vip%22%7D',
    "first-authorization": "1772671463061",
}

# ==================== 辅助函数 ====================

def build_search_params(
    regionid="110000,310000,440000,320000,330000",
    regcap="5000￥",
    esdate="2026-03-05￥2026-03-05",
    entname="",
    contact="",
    dom="",
    opscope="",
    nicid="",
    status="",
    enttype="",
    page_start=0,
    page_length=10
):
    """
    构建高级搜索参数
    
    Args:
        regionid: 地区代码（逗号分隔），默认：110000(北京),310000(上海),440000(广东),320000(江苏),330000(浙江)
        regcap: 注册资本（格式：金额￥），例如："5000￥" 表示5000万以上
        esdate: 成立日期（格式：开始日期￥结束日期）
        entname: 企业名称
        contact: 联系方式
        dom: 住所
        opscope: 经营范围
        nicid: 行业代码
        status: 经营状态
        enttype: 企业类型
        page_start: 分页起始位置（默认0）
        page_length: 每页数量（默认10）
    
    Returns:
        dict: 完整的请求参数
    """
    search_condition = {
        "contact": contact,
        "entname": entname,
        "dom": dom,
        "opscope": opscope,
        "nicid": nicid,
        "regionid": regionid,
        "regcap": regcap,
        "esdate": esdate,
        "status": status,
        "enttype": enttype,
        "orgtype": "",
        "ygrs": "",
        "sort_field": "",
        "enterprise_scale": "",
        "available_version": "",
        "tax_credit": "",
        "has_sm_ent": "",
        "has_jobinfo": "",
        "has_bid_notice": "",
        "has_bid_win": "",
        "has_ip_tminfo": "",
        "has_ip_patent": "",
        "has_soft_copyright": "",
        "has_work_copyright": "",
        "has_tuiguang_website": "",
        "has_icp": "",
        "has_ipr": "",
        "has_tuiguang_ios": "",
        "has_tuiguang_android": ""
    }
    
    ao_data = [
        {"name": "sEcho", "value": 2},
        {"name": "iColumns", "value": 10},
        {"name": "sColumns", "value": "id,name,contact,email,frname,status,regCap,entType,regDate,creditNo"},
        {"name": "iDisplayStart", "value": page_start},
        {"name": "iDisplayLength", "value": page_length},
        {"name": "cSearch_conditionData", "value": search_condition}
    ]
    
    return {
        "aoData": json.dumps(ao_data, ensure_ascii=False),
        "queryLimitType": 2,
        "queryType": "senior"
    }

# ==================== 默认请求体 ====================

# 使用辅助函数构建默认参数
REQUEST_DATA = build_search_params()

# ==================== 执行请求 ====================

def search_riskbird(data=None):
    """
    执行 RiskBird API 搜索
    
    Args:
        data: 请求数据（可选，默认使用 REQUEST_DATA）
    
    Returns:
        dict: API 响应数据
    """
    if data is None:
        data = REQUEST_DATA
    
    print(f"正在访问 RiskBird API...")
    print(f"URL: {SEARCH_API_URL}")
    print(f"请求参数: {json.dumps(data, ensure_ascii=False, indent=2)}")
    print()
    
    try:
        response = requests.post(
            SEARCH_API_URL,
            headers=HEADERS,
            cookies=COOKIES,
            json=data,
            timeout=30
        )
        
        print(f"HTTP 状态码: {response.status_code}")
        print()
        
        # 解析 JSON 响应
        result = response.json()
        
        # 格式化输出
        print("响应内容:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 保存到文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"response_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n响应已保存到: {output_file}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        print(f"原始响应: {response.text}")
        return None

# ==================== 区域代码查询 ====================

def get_region_tree(level=2):
    """
    获取行政区划树形结构
    
    Args:
        level (int): 层级深度
            - 1: 只返回省级
            - 2: 返回省级 + 市级
            - 3: 返回省级 + 市级 + 区级
    
    Returns:
        list: 行政区划树形结构
    """
    print(f"正在获取行政区划（level={level}）...")
    
    data = {'level': level, 'type': 'regionid_code'}
    
    try:
        response = requests.post(
            REGION_API_URL,
            headers=HEADERS,
            cookies=COOKIES,
            json=data,
            timeout=30
        )
        
        result = response.json()
        
        if result.get('success'):
            regions = result['data']
            print(f"✅ 成功获取 {len(regions)} 个省级行政区")
            return regions
        else:
            print(f"❌ 查询失败: {result.get('msg')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

def find_province_by_code(code):
    """
    根据省份代码获取省份信息及其城市列表
    
    Args:
        code (str): 省份代码（如 "320000"）
    
    Returns:
        dict: 省份信息（包含城市列表）
    """
    regions = get_region_tree(level=2)
    
    if regions:
        for province in regions:
            if province['code'] == code:
                return province
    
    return None

def find_province_by_name(name):
    """
    根据省份名称获取省份信息及其城市列表
    
    Args:
        name (str): 省份名称（如 "江苏省"）
    
    Returns:
        dict: 省份信息（包含城市列表）
    """
    regions = get_region_tree(level=2)
    
    if regions:
        for province in regions:
            if name in province['name']:
                return province
    
    return None

def list_all_provinces():
    """
    列出所有省份
    
    Returns:
        list: 省份列表
    """
    regions = get_region_tree(level=1)
    
    if regions:
        print("\n全国省级行政区列表：")
        print("=" * 60)
        for i, province in enumerate(regions, 1):
            print(f"{i:2d}. {province['name']} ({province['code']})")
        return regions
    
    return None

# ==================== Reusable API Functions ====================

def get_riskbird_request_data(token: str, app_uuid: str, search_params: dict) -> dict:
    """
    Build RiskBird API request data with provided token

    Args:
        token: JWT token
        app_uuid: App device UUID
        search_params: Search parameters from build_search_params

    Returns:
        dict: Complete request data
    """
    cookies = {
        "app-uuid": app_uuid,
        "app-device": "WEB",
        "token": token,
    }

    return {
        "headers": HEADERS,
        "cookies": cookies,
        "json": search_params
    }

def call_riskbird_search_api(token: str, app_uuid: str, search_params: dict) -> dict:
    """
    Call RiskBird search API with provided credentials

    Args:
        token: JWT token
        app_uuid: App device UUID
        search_params: Search parameters

    Returns:
        dict: API response
    """
    request_data = get_riskbird_request_data(token, app_uuid, search_params)

    try:
        response = requests.post(
            SEARCH_API_URL,
            headers=request_data["headers"],
            cookies=request_data["cookies"],
            json=request_data["json"],
            timeout=30
        )

        # Log response details for debugging
        logging.info(f"RiskBird API Response: status={response.status_code}")

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {'error': 'unauthorized', 'message': 'Token expired or invalid'}
        else:
            # Try to parse error response from API
            error_detail = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                error_detail += f" - {error_data}"
            except:
                # If not JSON, include text response
                if response.text:
                    error_detail += f" - {response.text[:200]}"

            logging.error(f"RiskBird API error: {error_detail}")
            return {'error': 'api_error', 'status_code': response.status_code, 'message': error_detail}

    except requests.exceptions.RequestException as e:
        logging.error(f"RiskBird API request failed: {e}")
        return {'error': 'request_failed', 'message': str(e)}

# ==================== 主程序 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("RiskBird API 工具集")
    print("=" * 60)
    print()
    
    # 选择功能
    print("请选择功能：")
    print("[1] 企业高级搜索")
    print("[2] 查询行政区划代码")
    print("[3] 查看省份列表")
    print("[0] 退出")
    print()
    
    choice = input("请选择（0/1/2/3）：").strip()
    
    if choice == "1":
        # 企业高级搜索
        print("\n" + "=" * 60)
        print("【企业高级搜索】")
        print("=" * 60)
        print()
        
        print("【示例1】使用默认参数搜索（注册资本5000万以上，今日成立）")
        print("-" * 60)
        result = search_riskbird()
        
    elif choice == "2":
        # 查询行政区划
        print("\n" + "=" * 60)
        print("【查询行政区划代码】")
        print("=" * 60)
        print()
        
        print("请输入省份名称或代码（如：江苏省 或 320000）：")
        province_input = input(">>> ").strip()
        
        if province_input.isdigit():
            # 输入的是代码
            province = find_province_by_code(province_input)
        else:
            # 输入的是名称
            province = find_province_by_name(province_input)
        
        if province:
            print(f"\n{province['name']} ({province['code']}) 的城市列表：")
            print(f"共 {len(province['children'])} 个城市")
            print("-" * 60)
            
            for city in province['children']:
                print(f"  - {city['name']} ({city['code']})")
            
            # 保存到文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"region_{province['code']}_{timestamp}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(province, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 数据已保存到: {output_file}")
        else:
            print(f"❌ 未找到省份: {province_input}")
    
    elif choice == "3":
        # 查看省份列表
        list_all_provinces()
    
    elif choice == "0":
        print("\n再见！")
    
    else:
        print("\n无效的选择")
