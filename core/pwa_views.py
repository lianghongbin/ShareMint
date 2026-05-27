from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponseNotFound


def _static_file(relative_path: str, content_type: str) -> FileResponse | HttpResponseNotFound:
    path = Path(settings.BASE_DIR) / 'static' / relative_path
    if not path.is_file():
        return HttpResponseNotFound()
    response = FileResponse(path.open('rb'), content_type=content_type)
    response['Cache-Control'] = 'public, max-age=3600'
    return response


def manifest_view(request):
    return _static_file('manifest.json', 'application/manifest+json')


def service_worker_view(request):
    response = _static_file('js/service-worker.js', 'application/javascript')
    if isinstance(response, HttpResponseNotFound):
        return response
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response
