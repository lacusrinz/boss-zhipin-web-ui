#!/usr/bin/env python3
"""
数据库查询工具
提供命令行接口查询 BOSS 直聘数据库
"""

import sys
from pathlib import Path
from database import BOSSDatabase


def print_menu():
    """打印菜单"""
    print("\n" + "=" * 60)
    print("BOSS 直聘数据库查询工具")
    print("=" * 60)
    print("\n请选择操作:")
    print("  1. 查看总体统计")
    print("  2. 按来源统计")
    print("  3. 查看岗位最多的企业 (Top 20)")
    print("  4. 搜索岗位")
    print("  5. 查看所有企业")
    print("  6. 导出数据为 JSON")
    print("  0. 退出")
    print("=" * 60)


def show_total_stats(db: BOSSDatabase):
    """显示总体统计"""
    print("\n" + "-" * 60)
    print("总体统计")
    print("-" * 60)

    stats = db.get_total_stats()
    print(f"\n企业总数: {stats.get('total_companies', 0)}")
    print(f"岗位总数: {stats.get('total_jobs', 0)}")
    print(f"有 URL 的企业: {stats.get('companies_with_url', 0)}")


def show_source_stats(db: BOSSDatabase):
    """显示来源统计"""
    print("\n" + "-" * 60)
    print("按来源统计")
    print("-" * 60)

    source_stats = db.get_source_stats()
    if source_stats:
        print(f"\n{'来源':<20} {'岗位数量':>10}")
        print("-" * 60)
        for source, count in source_stats:
            print(f"{source:<20} {count:>10}")
    else:
        print("暂无数据")


def show_top_companies(db: BOSSDatabase, limit: int = 20):
    """显示岗位数量最多的企业"""
    print(f"\n" + "-" * 60)
    print(f"岗位数量最多的企业 (Top {limit})")
    print("-" * 60)

    company_stats = db.get_company_stats()
    if company_stats:
        print(f"\n{'排名':<6} {'企业名称':<40} {'岗位数量':>10}")
        print("-" * 60)
        for idx, (company_name, job_count) in enumerate(company_stats[:limit], 1):
            print(f"{idx:<6} {company_name:<40} {job_count:>10}")
    else:
        print("暂无数据")


def search_jobs(db: BOSSDatabase):
    """搜索岗位"""
    print("\n" + "-" * 60)
    print("搜索岗位")
    print("-" * 60)

    keyword = input("\n请输入岗位名称关键词（留空显示全部）: ").strip()
    source = input("请输入数据来源（留空显示全部）: ").strip()
    limit_str = input("请输入显示数量限制（默认 50）: ").strip()
    limit = int(limit_str) if limit_str.isdigit() else 50

    jobs = db.search_jobs(
        keyword=keyword if keyword else None,
        source=source if source else None,
        limit=limit
    )

    if jobs:
        print(f"\n找到 {len(jobs)} 条记录:")
        print(f"\n{'序号':<6} {'岗位名称':<30} {'公司名称':<30} {'薪资':<15} {'地点':<20}")
        print("-" * 120)

        for idx, job in enumerate(jobs, 1):
            print(f"{idx:<6} {job['job_name'][:30]:<30} {job['company_name'][:30]:<30} "
                  f"{job['salary']:<15} {job['location']:<20}")

        # 询问是否显示详情
        show_detail = input("\n是否查看某个岗位的详细信息？(输入序号，留空跳过): ").strip()
        if show_detail.isdigit():
            idx = int(show_detail) - 1
            if 0 <= idx < len(jobs):
                job = jobs[idx]
                print("\n" + "-" * 60)
                print("岗位详情")
                print("-" * 60)
                print(f"岗位名称: {job['job_name']}")
                print(f"公司名称: {job['company_name']}")
                print(f"公司 URL: {job['company_url'] or '无'}")
                print(f"薪资: {job['salary']}")
                print(f"工作地点: {job['location']}")
                print(f"经验要求: {job['experience']}")
                print(f"学历要求: {job['education']}")
                print(f"数据来源: {job['source']}")
                print(f"采集时间: {job['collection_time']}")
    else:
        print("未找到匹配的岗位")


def show_all_companies(db: BOSSDatabase):
    """显示所有企业"""
    print("\n" + "-" * 60)
    print("所有企业列表")
    print("-" * 60)

    try:
        db.cursor.execute("""
            SELECT name, url,
                   (SELECT COUNT(*) FROM jobs WHERE company_id = companies.id) as job_count
            FROM companies
            ORDER BY job_count DESC
        """)
        companies = db.cursor.fetchall()

        if companies:
            print(f"\n{'企业名称':<40} {'岗位数量':>10} {'URL':<50}")
            print("-" * 110)

            for name, url, job_count in companies:
                url_display = url[:47] + '...' if url and len(url) > 50 else (url or '无')
                print(f"{name[:40]:<40} {job_count:>10} {url_display:<50}")
        else:
            print("暂无企业数据")

    except Exception as e:
        print(f"查询失败: {e}")


def export_to_json(db: BOSSDatabase):
    """导出数据为 JSON"""
    print("\n" + "-" * 60)
    print("导出数据为 JSON")
    print("-" * 60)

    data = db.export_to_dict()

    # 保存到文件
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "boss_jobs_export.json"

    import json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 数据已导出到: {output_file}")
    print(f"  企业数量: {len(data['companies'])}")
    print(f"  岗位数量: {len(data['jobs'])}")


def main():
    """主函数"""
    # 创建数据库实例
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "data" / "boss_jobs.db"
    db = BOSSDatabase(str(db_path))

    # 连接数据库
    if not db.connect():
        print("数据库连接失败")
        return 1

    # 检查数据库是否存在表
    try:
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = db.cursor.fetchall()
        if not tables or len(tables) < 2:
            print("数据库尚未初始化，请先运行 extract_jobs_v7.py 提取数据")
            db.close()
            return 1
    except Exception as e:
        print(f"数据库检查失败: {e}")
        db.close()
        return 1

    # 主循环
    while True:
        print_menu()
        choice = input("\n请输入选项 (0-6): ").strip()

        if choice == '0':
            print("\n再见！")
            break
        elif choice == '1':
            show_total_stats(db)
        elif choice == '2':
            show_source_stats(db)
        elif choice == '3':
            show_top_companies(db)
        elif choice == '4':
            search_jobs(db)
        elif choice == '5':
            show_all_companies(db)
        elif choice == '6':
            export_to_json(db)
        else:
            print("\n无效选项，请重新选择")

        input("\n按 Enter 继续...")

    # 关闭数据库
    db.close()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断程序")
        sys.exit(130)
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
