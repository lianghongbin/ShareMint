def app_context(request):
    match = getattr(request, 'resolver_match', None)
    return {
        'current_url_name': match.url_name if match else '',
    }
