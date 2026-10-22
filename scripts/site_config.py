"""Resolve deployment URLs for a custom domain or a GitHub Pages project path."""
import os
from urllib.parse import urlsplit
from content import ROOT, read_yaml


def base_url(root=ROOT):
    config = root/'hugo.yaml' if (root/'hugo.yaml').is_file() else ROOT/'hugo.yaml'
    value = os.environ.get('HUGO_BASEURL') or read_yaml(config)['baseURL']
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError('The website base URL must be an http(s) address without credentials, query or fragment')
    return value.rstrip('/') + '/'


def site_path(value, root=ROOT):
    if not value or not value.startswith('/') or value.startswith('//'):
        return value
    prefix = urlsplit(base_url(root)).path
    return prefix + value.lstrip('/')


def absolute_url(value, root=ROOT):
    return base_url(root) + value.lstrip('/')
