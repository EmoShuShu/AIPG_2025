import requests
from bs4 import BeautifulSoup
import re
import ssl

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

class Tls12HttpAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        context = create_urllib3_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        super().init_poolmanager(
            connections,
            maxsize,
            block,
            ssl_context=context
        )

# 创建并配置会话
session = requests.Session()
session.mount("https://", Tls12HttpAdapter())
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})


def discover_all_page_urls(main_url):
    """
    从主页面 https://blogs.magicjudges.org/rules/ipg/ 发现所有规则条款的链接。
    """
    urls = set()
    print(f"正在从主页面 <{main_url}> 查找所有规则链接...")

    try:
        response = session.get(main_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        pattern = re.compile(r'/rules/ipg\d+(-\d+)?/?$')
        for link in soup.find_all('a', href=pattern):
            href = link.get('href')
            if href:
                if not href.startswith('http'):
                    href = requests.compat.urljoin(main_url, href)
                
                normalized_href = href.rstrip('/')
                urls.add(normalized_href)

    except requests.exceptions.RequestException as e:
        print(f"错误: 访问主页面 {main_url} 失败: {e}")
        return []

    if not urls:
        print("警告: 未能在主页面上找到任何符合 '/rules/ipg...' 格式的链接。")
        return []
    
    return list(urls)

def extract_info_from_url(url):
    """
    从给定的URL中提取所有class="alert alert-info"的div中的纯文本，并保留段落结构。
    """
    extracted_texts = []
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        info_divs = soup.find_all('div', class_='alert alert-info', role='alert')
        for div in info_divs:
            paragraphs = []
            
            for p in div.find_all('p'):
                text = p.get_text(strip=True)
                if text:
                    paragraphs.append(text)
                p.decompose()

            remaining_text = div.get_text(strip=True)
            if remaining_text:
                paragraphs.insert(0, remaining_text)
            
            if paragraphs:
                extracted_texts.extend(paragraphs)
            
    except requests.exceptions.RequestException as e:
        print(f"  -> 警告: 处理页面 {url} 时出错: {e}")
    return extracted_texts

def get_natural_sort_key(url):
    """
    为URL生成一个用于自然排序的键。
    - '.../ipg1-2' -> (1, 2)
    - '.../ipg1'   -> (1, 0)
    """
    match_section = re.search(r'ipg(\d+)-(\d+)', url)
    if match_section:
        chapter = int(match_section.group(1))
        section = int(match_section.group(2))
        return (chapter, section)
    
    match_chapter = re.search(r'ipg(\d+)', url)
    if match_chapter:
        chapter = int(match_chapter.group(1))
        return (chapter, 0)
        
    return (999, 999)

# --- 主程序 ---
if __name__ == "__main__":
    main_page_url = 'https://blogs.magicjudges.org/rules/ipg/'
    output_filename = 'extracted_rules.txt'
    
    # --- 已修正此处的变量名 ---
    rule_urls = discover_all_page_urls(main_page_url)
    
    if not rule_urls:
        print("程序终止，因为未能发现任何可处理的URL。")
    else:
        print(f"发现 {len(rule_urls)} 个不重复的规则页面。开始提取信息...")
        print("-" * 50)
        
        all_extracted_data = {}
        
        sorted_urls_for_processing = sorted(rule_urls, key=get_natural_sort_key)

        for i, url in enumerate(sorted_urls_for_processing):
            print(f"正在处理: [{i+1}/{len(sorted_urls_for_processing)}] {url}")
            texts = extract_info_from_url(url)
            if texts:
                all_extracted_data[url] = texts
        
        print("\n" + "=" * 50)
        print("所有页面处理完毕！")
        
        if not all_extracted_data:
            print("在所有找到的子页面中，均未提取到任何目标信息。")
        else:
            print(f"正在将 {len(all_extracted_data)} 个页面的结果按章节排序并写入文件: {output_filename}")
            
            sorted_urls_for_writing = sorted(all_extracted_data.keys(), key=get_natural_sort_key)
            
            try:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    for url in sorted_urls_for_writing:
                        texts = all_extracted_data[url]
                        
                        header_match = re.search(r'ipg\d+(-\d+)?', url)
                        simple_header = header_match.group(0) if header_match else url
                        
                        f.write(f"--- {simple_header} ---\n")
                        for text in texts:
                            f.write(f"{text}\n")
                        f.write("\n")
                print(f"成功！所有提取内容已保存至 {output_filename}")
            except IOError as e:
                print(f"错误: 写入文件失败: {e}")