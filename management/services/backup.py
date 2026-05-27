from datetime import datetime
from io import StringIO
from pathlib import Path

from django.core.management import call_command


def build_backup() -> tuple[str, str]:
    """全量 dumpdata 备份为 JSON 字符串。"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'sharemint_backup_{timestamp}.json'
    output = StringIO()
    call_command(
        'dumpdata',
        '--natural-foreign',
        '--natural-primary',
        '--indent',
        '2',
        stdout=output,
    )
    return filename, output.getvalue()


def restore_backup(filepath: Path) -> None:
    """从 JSON 文件 loaddata 还原。"""
    call_command('loaddata', str(filepath))
