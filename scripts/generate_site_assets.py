import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import yaml
from datetime import datetime

CURRENT_DIR = os.path.abspath(os.getcwd())
PUBLIC_DIR = os.path.join(CURRENT_DIR, 'public')

def load_config():
    config_path = os.path.join(CURRENT_DIR, 'config.yaml')
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            # Ensure sitemap_exclude_list is always a list, even if not specified in config
            config['sitemap_exclude_list'] = config.get('sitemap_exclude_list', [])
            return config
    except FileNotFoundError:
        print(f"Error: config.yaml file not found at {config_path}")
        return {'sitemap_exclude_list': []}
    except yaml.YAMLError as e:
        print(f"Error parsing config.yaml: {e}")
        return {'sitemap_exclude_list': []}

def load_pages_config():
    pages_path = os.path.join(CURRENT_DIR, 'data', 'pages.yaml')
    try:
        with open(pages_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Error: pages.yaml file not found at {pages_path}")
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing pages.yaml: {e}")
        return {}

def get_html_files(directory):
    html_files = []
    for root, _, files in os.walk(directory):
        if 'node_modules' in root:
            continue
        for file in files:
            if file.lower().endswith('.html'):
                html_files.append(os.path.join(root, file))
    return html_files

def create_sitemap(base_url, sitemap_exclude_list):
    html_files = get_html_files(PUBLIC_DIR)
    pages_config = load_pages_config()
    root = ET.Element("urlset")
    root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    current_date = datetime.now().strftime('%Y-%m-%d')

    for file in html_files:
        relative_path = os.path.relpath(file, PUBLIC_DIR)
        url_path = relative_path.replace(os.path.sep, '/').replace('.html', '')
        if url_path == 'index':
            url_path = ''
        
        # Skip this file if it's in the sitemap_exclude_list
        if url_path in sitemap_exclude_list:
            continue

        url = f"{base_url}/{url_path}"

        # Get page config if available
        page_config = pages_config.get(url_path, {})

        url_element = ET.SubElement(root, "url")
        ET.SubElement(url_element, "loc").text = url

        # Use last_mod from pages.yaml if available, otherwise use current date
        last_mod = page_config.get('last_mod', current_date)
        ET.SubElement(url_element, "lastmod").text = last_mod

        priority = '1.0' if url == base_url or url == f"{base_url}/" else '0.8'
        ET.SubElement(url_element, "priority").text = priority

    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    sitemap_path = os.path.join(PUBLIC_DIR, 'sitemap.xml')
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write(xml_str)
    print(f'Sitemap created successfully at {sitemap_path}!')

def create_robots_txt(base_url):
    robots_txt = f"""User-agent: *
Allow: /
Sitemap: {base_url}/sitemap.xml"""
    robots_txt_path = os.path.join(PUBLIC_DIR, 'robots.txt')
    with open(robots_txt_path, 'w') as f:
        f.write(robots_txt)
    print(f'robots.txt created successfully at {robots_txt_path}!')

def main():
    config = load_config()
    base_url = config.get('base_url', '')
    if not base_url:
        print("Error: base_url not found in config.yaml")
        return

    sitemap_exclude_list = config.get('sitemap_exclude_list', [])

    if config.get('generate_sitemap', False):
        create_sitemap(base_url, sitemap_exclude_list)
    else:
        print("Sitemap generation is disabled in config.")

    if config.get('generate_robots', False):
        create_robots_txt(base_url)
    else:
        print("robots.txt generation is disabled in config.")

if __name__ == "__main__":
    main()