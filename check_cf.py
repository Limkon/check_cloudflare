import requests
import concurrent.futures
import csv
import os

# 读取域名列表的文件路径 (请确保你的仓库中有这个文件，每行一个域名)
输入文件 = 'domains.txt'
# 保存检测结果的文件路径
输出文件 = 'result.csv'

def 检测_cloudflare(域名):
    """
    检测单个域名是否使用了 Cloudflare CDN
    """
    域名 = 域名.strip()
    if not 域名:
        return None

    # 如果没有指定协议，默认使用 https 测试
    if not 域名.startswith(('http://', 'https://')):
        测试链接 = 'https://' + 域名
    else:
        测试链接 = 域名

    try:
        # 加上常见的请求头，防止被部分网站的安全策略直接拦截
        请求头 = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # 使用 timeout 防止遇到死链时脚本无限期卡死
        响应 = requests.get(测试链接, headers=请求头, timeout=10, allow_redirects=True)
        响应头 = 响应.headers

        # 将所有的响应头键转换为小写，方便统一匹配
        响应头小写 = {k.lower(): v for k, v in 响应头.items()}

        # 核心检测逻辑：检查 Server 字段和 CF-RAY 字段
        使用了_cf = "否"
        if 'server' in 响应头小写 and 'cloudflare' in 响应头小写['server'].lower():
            使用了_cf = "是"
        elif 'cf-ray' in 响应头小写:
            使用了_cf = "是"

        print(f"检测完成: {域名} -> 状态码: {响应.status_code}, Cloudflare: {使用了_cf}")
        return [域名, 使用了_cf, 响应.status_code, "正常"]

    except requests.exceptions.RequestException as 错误:
        print(f"检测失败: {域名} -> 无法连接或超时")
        return [域名, "未知", "无", f"请求失败"]

def 主程序():
    # 检查存放域名的输入文件是否存在
    if not os.path.exists(输入文件):
        print(f"错误：找不到输入文件 {输入文件}，请确保文件存在。")
        return

    # 读取域名列表
    with open(输入文件, 'r', encoding='utf-8') as 文件:
        域名列表 = 文件.readlines()

    结果列表 = []
    
    # 使用线程池并发检测，显著提高批量检测的速度。这里设置最大线程数为 10
    print(f"开始批量检测，共计 {len(域名列表)} 个网址...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as 执行器:
        # 执行器会并发处理，并将结果收集起来
        for 结果 in 执行器.map(检测_cloudflare, 域名列表):
            if 结果:
                结果列表.append(结果)

    # 将最终结果保存到 CSV 文件中 (使用 utf-8-sig 防止在 Windows Excel 中打开乱码)
    with open(输出文件, 'w', newline='', encoding='utf-8-sig') as 结果文件:
        写入器 = csv.writer(结果文件)
        写入器.writerow(['域名', '是否使用Cloudflare', 'HTTP状态码', '备注信息'])
        写入器.writerows(结果列表)
        
    print(f"所有网站检测已完成，结果已成功保存至 {输出文件}")

if __name__ == "__main__":
    主程序()
