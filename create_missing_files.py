import os

# Templates for the generated files
forms_template = '''from django import forms

# Create your forms here.
'''

urls_template = '''from django.urls import path
from . import views

urlpatterns = [
    # path('', views.home, name='home'),
]
'''

# Helper to detect Django app directories
def is_django_app(path):
    return os.path.isfile(os.path.join(path, 'models.py')) or os.path.isfile(os.path.join(path, 'views.py'))

def create_file_if_missing(app_path, filename, content):
    file_path = os.path.join(app_path, filename)
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Created {filename} in {app_path}")
    else:
        print(f"{filename} already exists in {app_path}, skipping.")

def update_project_urls(project_root, project_name, apps):
    urls_path = os.path.join(project_root, project_name, 'urls.py')
    if not os.path.exists(urls_path):
        print(f"[!] Main urls.py not found at {urls_path}. Skipping update.")
        return

    with open(urls_path, 'r') as f:
        content = f.read()

    modified = False
    if 'from django.urls' not in content:
        content = 'from django.urls import path, include\n' + content
        modified = True

    if 'urlpatterns' not in content:
        content += '\nurlpatterns = []\n'
        modified = True

    for app in apps:
        include_line = f"path('{app}/', include('{app}.urls'))"
        if include_line not in content:
            # insert just before closing bracket of urlpatterns
            content = content.replace('urlpatterns = [', f'urlpatterns = [\n    {include_line},')
            modified = True

    if modified:
        with open(urls_path, 'w') as f:
            f.write(content)
        print(f"✅ Updated {urls_path} to include app URLs.")
    else:
        print("🔁 No changes needed in main urls.py.")

def main():
    project_root = os.getcwd()
    apps = []

    # Detect project name (directory that contains settings.py)
    project_name = ''
    for item in os.listdir(project_root):
        if os.path.isdir(item) and os.path.isfile(os.path.join(item, 'settings.py')):
            project_name = item
            break

    if not project_name:
        print("❌ Could not detect Django project (missing settings.py).")
        return

    for item in os.listdir(project_root):
        app_path = os.path.join(project_root, item)
        if os.path.isdir(app_path) and is_django_app(app_path):
            apps.append(item)
            create_file_if_missing(app_path, 'forms.py', forms_template)
            create_file_if_missing(app_path, 'urls.py', urls_template)

    update_project_urls(project_root, project_name, apps)

if __name__ == '__main__':
    main()
