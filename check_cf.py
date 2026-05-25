import requests
import concurrent.futures
import csv
import os
import zipfile
import io

# 配置文件路径及参数
输入文件 = 'domains.txt'
输出文件 = 'result.csv'
进度文件 = 'progress.txt'
每次检测数量 = 2000
# 第一次运行时自动下载的域名数量（提取前10万个）
初始下载数量 = 100000

def 下载并生成域名列表():
    """
    如果不存在 domains.txt，则从 Tranco 自动下载最新的全球 Top 1M 列表并提取前 10万个
    """
    if os.path.exists(输入文件):
        return

    print(f"未找到 {输入文件}，正在自动下载全球顶级域名列表 (Tranco Top 1M)...")
    try:
        url = "https://tranco-list.eu/top-1m.csv.zip"
        请求头 = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        # 下载 zip 文件流
        响应 = requests.get(url, headers=请求头, stream=True, timeout=30)
        响应.raise_for_status()

        print("下载完成，正在解压并提取前 100,000 个域名...")
        
        # 在内存中解压并读取
        with zipfile.ZipFile(io.BytesIO(响应.content)) as 压缩包:
            csv_文件名 = 压缩包.namelist()[0]
            with 压缩包.open(csv_文件名) as 文件:
                # 读取所有行并解码
                所有行 = 文件.read().decode('utf-8').splitlines()

        # 提取域名 (Tranco 格式为: 排名,域名)
        提取的域名 = []
        for 行 in 所有行[:初始下载数量]:
            if ',' in 行:
                域名 = 行.split(',')[1].strip()
                提取的域名.append(域名)

        # 写入 domains.txt
        with open(输入文件, 'w', encoding='utf-8') as 文件:
            for 域名 in 提取的域名:
                文件.write(域名 + '\n')
                
        print(f"成功获取并保存了 {len(提取的域名)} 个域名至 {输入文件}！")
        
    except Exception as 错误:
        print(f"自动下载域名列表失败: {错误}")
        # 如果下载失败，停止后续运行
        exit(1)

def 检测_cloudflare(域名):
    """
    检测单个域名是否使用了 Cloudflare CDN
    """
    if not 域名:
        return None

    if not 域名.startswith(('http://', 'https://')):
        测试链接 = 'https://' + 域名
    else:
        测试链接 = 域名

    try:
        请求头 = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        响应 = requests.get(测试链接, headers=请求头, timeout=10, allow_redirects=True)
        响应头 = 响应.headers
        响应头小写 = {k.lower(): v for k, v in 响应头.items()}

        使用了_cf = "否"
        if 'server' in 响应头小写 and 'cloudflare' in 响应头小写['server'].lower():
            使用了_cf = "是"
        elif 'cf-ray' in 响应头小写:
            使用了_cf = "是"

        print(f"检测完成: {域名} -> 状态码: {响应.status_code}, Cloudflare: {使用了_cf}")
        return [域名, 使用了_cf, 响应.status_code, "正常"]

    except requests.exceptions.RequestException as 错误:
        print(f"检测失败: {域名} -> 无法连接或超时")
        return [域名, "未知", "无", "请求失败"]

def 获取当前进度():
    """
    从进度文件中读取上次检测到的行数
    """
    if os.path.exists(进度文件):
        with open(进度文件, 'r', encoding='utf-8') as 文件:
            try:
                内容 = 文件.read().strip()
                if 内容:
                    return int(内容)
            except ValueError:
                return 0
    return 0

def 保存当前进度(新进度):
    """
    将新的进度行数写入进度文件
    """
    with open(进度文件, 'w', encoding='utf-8') as 文件:
        文件.write(str(新进度))

def 主程序():
    # 第一步：检查并自动下载域名源数据
    下载并生成域名列表()

    # 读取全部域名列表
    with open(输入文件, 'r', encoding='utf-8') as 文件:
        所有行 = 文件.readlines()
        域名列表 = [行.strip() for 行 in 所有行 if 行.strip()]

    总数量 = len(域名列表)
    当前起始位置 = 获取当前进度()

    if 当前起始位置 >= 总数量:
        print(f"进度显示已检测 {当前起始位置} 个。所有域名已经全部检测完毕，无需再次运行。")
        return

    # 计算本次要检测的范围
    当前结束位置 = min(当前起始位置 + 每次检测数量, 总数量)
    待检测列表 = 域名列表[当前起始位置:当前结束位置]

    print(f"总计 {总数量} 个网址。")
    print(f"本次运行从第 {当前起始位置 + 1} 个开始，检测到第 {当前结束位置} 个，共计 {len(待检测列表)} 个。")

    结果列表 = []
    
    # 并发检测
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as 执行器:
        for 结果 in 执行器.map(检测_cloudflare, 待检测列表):
            if 结果:
                结果列表.append(结果)

    # 写入结果：如果是从第0个开始，则覆盖写入并添加表头；否则追加写入
    写入模式 = 'w' if 当前起始位置 == 0 else 'a'
    with open(输出文件, 写入模式, newline='', encoding='utf-8-sig') as 结果文件:
        写入器 = csv.writer(结果文件)
        if 写入模式 == 'w':
            写入器.writerow(['域名', '是否使用Cloudflare', 'HTTP状态码', '备注信息'])
        写入器.writerows(结果列表)
        
    # 保存新的进度
    保存当前进度(当前结束位置)
    print(f"本次 {len(待检测列表)} 个网站检测已完成。")
    print(f"结果已成功追加至 {输出文件}，进度文件已更新为 {当前结束位置}。")

if __name__ == "__main__":
    主程序()
