#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    import sys
    import os
    print(f"DEBUG: sys.path = {sys.path}")
    print(f"DEBUG: CWD = {os.getcwd()}")
    print(f"DEBUG: ROOT_DIR = {os.listdir('.')}")
    if os.path.exists('authentication'):
        print(f"DEBUG: authentication/ exists, contents: {os.listdir('authentication')}")
    else:
        print("DEBUG: authentication/ directory NOT FOUND in CWD")

    # Ensure the project root is in sys.path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
