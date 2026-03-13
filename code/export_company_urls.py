#!/usr/bin/env python3
"""
导出企业 URL 列表
生成 HTML 文件，包含所有企业 URL，方便在浏览器中打开查看
"""
import sys
from pathlib import Path
from datetime import datetime

from database import BOSSDatabase


def export_company_urls(db: BOSSDatabase, output_file: str):
    """导出企业 URL 到 HTML 文件"""
    print("正在获取企业 URL...")

    # 获取所有有 URL 的企业
    db.cursor.execute("""
        SELECT name, url
        FROM companies
        WHERE url IS NOT NULL AND url != ''
        ORDER BY name
    """)

    companies = db.cursor.fetchall()

    if not companies:
        print("没有找到有 URL 的企业")
        return

    print(f"找到 {len(companies)} 家有 URL 的企业")

    # 生成 HTML 文件
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BOSS 直聘企业 URL 列表</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        h1 {
            color: #333;
            margin-bottom: 30px;
            font-size: 28px;
        }

        .info {
            color: #666;
            margin-bottom: 20px;
            font-size: 14px;
        }

        .stats {
            background: #f0f7ff;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 30px;
            border-left: 4px solid #4472C4;
        }

        .stats strong {
            color: #4472C4;
        }

        .search-box {
            margin-bottom: 20px;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 4px;
        }

        .search-box input {
            width: 100%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }

        th {
            background: #4472C4;
            color: white;
            font-weight: 600;
            position: sticky;
            top: 0;
        }

        tr:hover {
            background: #f5f5f5;
        }

        .url-link {
            color: #4472C4;
            text-decoration: none;
            word-break: break-all;
        }

        .url-link:hover {
            text-decoration: underline;
        }

        .company-name {
            font-weight: 600;
            color: #333;
        }

        .count {
            display: inline-block;
            padding: 2px 8px;
            background: #4472C4;
            color: white;
            border-radius: 12px;
            font-size: 12px;
            margin-left: 10px;
        }

        .copy-btn {
            padding: 4px 12px;
            background: #4472C4;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 10px;
        }

        .copy-btn:hover {
            background: #33539e;
        }

        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #999;
            font-size: 14px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏢 BOSS 直聘企业 URL 列表</h1>

        <div class="info">
            生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
        </div>

        <div class="search-box">
            <input type="text" id="searchInput" placeholder="搜索企业名称..." onkeyup="searchTable()">
        </div>

        <div class="stats">
            总计 <strong>""" + str(len(companies)) + """</strong> 家企业，
            每家企业有独立的招聘页面，可以查看该企业的所有招聘岗位。
        </div>

        <table id="companyTable">
            <thead>
                <tr>
                    <th style="width: 50px;">序号</th>
                    <th>企业名称</th>
                    <th>招聘页面链接</th>
                    <th style="width: 100px;">操作</th>
                </tr>
            </thead>
            <tbody>
"""

    # 添加企业行
    for idx, (name, url) in enumerate(companies, 1):
        html_content += f"""
                <tr>
                    <td>{idx}</td>
                    <td class="company-name">{name}</td>
                    <td><a href="{url}" target="_blank" class="url-link">{url}</a></td>
                    <td>
                        <button class="copy-btn" onclick="copyToClipboard('{url}')">复制链接</button>
                    </td>
                </tr>
"""

    html_content += """
            </tbody>
        </table>

        <div class="footer">
            <p>提示：点击链接可在新窗口中打开企业招聘页面</p>
            <p>数据来源：BOSS 直聘数据库</p>
        </div>
    </div>

    <script>
        function searchTable() {
            var input, filter, table, tr, td, i, txtValue;
            input = document.getElementById('searchInput');
            filter = input.value.toUpperCase();
            table = document.getElementById('companyTable');
            tr = table.getElementsByTagName('tr');

            for (i = 1; i < tr.length; i++) {
                td = tr[i].getElementsByTagName('td')[1]; // 企业名称列
                if (td) {
                    txtValue = td.textContent || td.innerText;
                    if (txtValue.toUpperCase().indexOf(filter) > -1) {
                        tr[i].style.display = '';
                    } else {
                        tr[i].style.display = 'none';
                    }
                }
            }
        }

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(function() {
                alert('链接已复制到剪贴板！');

                // 显示复制成功提示
                var originalText = event.target.textContent;
                event.target.textContent = '已复制';
                setTimeout(function() {
                    event.target.textContent = originalText;
                }, 2000);
            }).catch(function(err) {
                alert('复制失败，请手动复制链接');
            });
        }
    </script>
</body>
</html>
"""

    # 保存文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✓ 已生成 HTML 文件: {output_file}")
    print(f"  包含 {len(companies)} 家企业的 URL")


def main():
    """主函数"""
    print("=" * 60)
    print("BOSS 直聘企业 URL 导出工具")
    print("=" * 60)

    # 配置路径
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "data" / "boss_jobs.db"

    # 输出文件
    output_dir = base_dir / "reports"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output_file = output_dir / f'企业URL列表_{timestamp}.html'

    # 连接数据库
    db = BOSSDatabase(str(db_path))

    if not db.connect():
        print("数据库连接失败")
        return 1

    # 导出 URL
    export_company_urls(db, str(output_file))

    # 统计信息
    stats = db.get_total_stats()
    print(f"\n数据库统计:")
    print(f"  企业总数: {stats.get('total_companies', 0)}")
    print(f"  有 URL 的企业: {stats.get('companies_with_url', 0)}")

    db.close()

    print(f"\n提示: 在浏览器中打开 {output_file} 即可查看所有企业 URL")

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
