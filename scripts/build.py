import os
import shutil
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import yaml
import subprocess
import jsmin
import htmlmin

ORIGINAL_DIR = os.path.abspath(os.getcwd())
PUBLIC_DIR = os.path.join(ORIGINAL_DIR, 'public')
print(f"Current working directory: {ORIGINAL_DIR}\n")

def load_config():
    try:
        config_path = os.path.join(ORIGINAL_DIR, 'data', 'pages.yaml')
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        print("pages.yaml loaded successfully\n")
        return config
    except FileNotFoundError:
        print(f"Error: pages.yaml file not found at {config_path}\n")
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing pages.yaml: {e}\n")
        return {}

def load_site_config():
    try:
        config_path = os.path.join(ORIGINAL_DIR, 'config.yaml')
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        version = config.get('version', '1.0.0')
        enable_analytics = config.get('enable_analytics', False)
        minify_html = config.get('minify_html', False)
        minify_js = config.get('minify_js', False)
        print(f"Updated to version {version} successfully\n")
        if enable_analytics:
            print("Analytics enabled\n")
        else:
            print("Analytics disabled\n")
        print(f"HTML minification: {'enabled' if minify_html else 'disabled'}\n")
        print(f"JS minification: {'enabled' if minify_js else 'disabled'}\n")
        return config
    except FileNotFoundError:
        print(f"Error: config.yaml file not found at {config_path}\n")
        return {'version': '1.0.0', 'enable_analytics': False, 'minify_html': False, 'minify_js': False}
    except yaml.YAMLError as e:
        print(f"Error parsing config.yaml: {e}\n")
        return {'version': '1.0.0', 'enable_analytics': False, 'minify_html': False, 'minify_js': False}

def create_jinja_env():
    return Environment(
        loader=FileSystemLoader([
            os.path.join(ORIGINAL_DIR, 'src', 'templates'),
            os.path.join(ORIGINAL_DIR, 'src', 'content')
        ]),
        autoescape=True
    )

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def minify_js(js_content):
    return jsmin.jsmin(js_content)

def minify_html(html_content):
    return htmlmin.minify(html_content, remove_empty_space=True, remove_comments=True)

def build_pages(env, config, site_config):
    public_dir = os.path.join(ORIGINAL_DIR, 'public')
    ensure_dir(public_dir)

    default_metadata = {
        'title': None,
        'description': None,
        'keywords': None,
        'author': None,
        'og_title': None,
        'og_description': None,
        'og_image': None,
        'og_url': None,
        'twitter_title': None,
        'twitter_description': None,
        'twitter_image': None,
        'favicon': None,
        'canonical_url': None,
    }

    version = site_config.get('version', '1.0.0')
    enable_analytics = site_config.get('enable_analytics', False)
    minify_html_flag = site_config.get('minify_html', False)

    # Get all HTML files in the content folder
    content_dir = os.path.join(ORIGINAL_DIR, 'src', 'content')
    html_files = [f for f in os.listdir(content_dir) if f.endswith('.html')]

    for html_file in html_files:
        page = html_file[:-5]  # Remove .html extension
        
        if page not in config:
            print(f"Warning: No config found for {html_file} in pages.yaml. Rendering with default config.\n")
            page_data = {}
        else:
            page_data = config[page]

        try:
            metadata = {**default_metadata, **page_data, 'version': version, 'enable_analytics': enable_analytics}
            
            # Check for missing metadata and collect missing keys
            missing_keys = [key for key in default_metadata.keys() if key not in page_data]
            if missing_keys:
                print(f"Warning: The following metadata is missing for {page} in pages.yaml: {', '.join(missing_keys)}\n")

            template = env.get_template(html_file)
            output = template.render(**metadata)
            
            if minify_html_flag:
                output = minify_html(output)
            
            output_path = os.path.join(public_dir, html_file)
            ensure_dir(os.path.dirname(output_path))
            with open(output_path, 'w') as file:
                file.write(output)
            print(f"Successfully rendered {'and minified ' if minify_html_flag else ''}{html_file}\n")
        except TemplateNotFound:
            print(f"Error: Template {html_file} not found\n")
        except Exception as e:
            print(f"Error rendering template {html_file}: {str(e)}\n")

def copy_static_files(site_config):
    minify_js_flag = site_config.get('minify_js', False)
    static_dirs = {
        'assets/images': 'public/images',
        'assets/icons': 'public/icons',
        'assets/js': 'public/js'
    }
    for src, dest in static_dirs.items():
        src_path = os.path.join(ORIGINAL_DIR, src)
        dest_path = os.path.join(ORIGINAL_DIR, dest)
        if os.path.exists(src_path):
            ensure_dir(dest_path)
            if src == 'assets/js':
                for js_file in os.listdir(src_path):
                    if js_file.endswith('.js'):
                        with open(os.path.join(src_path, js_file), 'r') as f:
                            js_content = f.read()
                        if minify_js_flag:
                            js_content = minify_js(js_content)
                        with open(os.path.join(dest_path, js_file), 'w') as f:
                            f.write(js_content)
                print(f"Copied {'and minified ' if minify_js_flag else ''}JS files from {src_path} to {dest_path}\n")
            else:
                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                print(f"Copied {src_path} to {dest_path}\n")
    print("Assets copied successfully.\n")

def build_css():
    try:
        input_file = os.path.join(ORIGINAL_DIR, "assets", "css", "styles.css")
        print(input_file)
        output_file = os.path.join(ORIGINAL_DIR, "public", "styles.css")
        print(output_file)
        config_file = os.path.join(ORIGINAL_DIR, "tailwind.config.js")

        # Run the tailwindcss command using subprocess
        subprocess.run([
            "tailwindcss",
            "-i", input_file,
            "-o", output_file,
            "-c", config_file,
            "--minify"
        ], check=True)
        
        print("CSS built successfully\n")
    except subprocess.CalledProcessError as e:
        print(f"Error building CSS: {e}\n")
    except Exception as e:
        print(f"General error: {e}\n")

def run_script(script_path):
    try:
        subprocess.run(['python', script_path], check=True)
        print(f"Successfully ran {script_path}\n")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}\n")
        raise

def main():
    os.chdir(ORIGINAL_DIR)
    page_config = load_config()
    site_config = load_site_config()
    env = create_jinja_env()
    build_css()
    build_pages(env, page_config, site_config)
    copy_static_files(site_config)
    
    scripts = [
        os.path.join(ORIGINAL_DIR, 'scripts', 'generate_site_assets.py'),
        # Add more scripts here if needed
    ]
    
    for script in scripts:
        run_script(script)

    print("Build completed successfully!\n")

if __name__ == "__main__":
    main()
