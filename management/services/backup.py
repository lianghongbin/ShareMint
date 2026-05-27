import json
from datetime import datetime
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.serializers import serialize


def ensure_backup_dir() -> Path:
    backup_dir = Path(settings.BACKUP_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_backup() -> Path:
    """全量 dumpdata 备份为 JSON 文件。"""
    backup_dir = ensure_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = backup_dir / f'sharemint_backup_{timestamp}.json'

    output = StringIO()
    call_command(
        'dumpdata',
        '--natural-foreign',
        '--natural-primary',
        '--indent',
        '2',
        stdout=output,
    )
    filepath.write_text(output.getvalue(), encoding='utf-8')
    return filepath


def restore_backup(filepath: Path) -> None:
    """从 JSON 文件 loaddata 还原。"""
    call_command('loaddata', str(filepath))


def list_backups() -> list[Path]:
    backup_dir = ensure_backup_dir()
    return sorted(backup_dir.glob('sharemint_backup_*.json'), reverse=True)
