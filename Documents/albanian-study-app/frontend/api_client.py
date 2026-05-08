import httpx
from config import API_BASE_URL

_client = httpx.Client(base_url=API_BASE_URL, timeout=60.0)


def get(path: str, **kwargs) -> dict:
    r = _client.get(path, **kwargs)
    r.raise_for_status()
    return r.json()


def post(path: str, json: dict = None, files=None, **kwargs) -> dict:
    r = _client.post(path, json=json, files=files, **kwargs)
    r.raise_for_status()
    return r.json()


def put(path: str, json: dict = None, **kwargs) -> dict:
    r = _client.put(path, json=json, **kwargs)
    r.raise_for_status()
    return r.json()


def delete(path: str, **kwargs) -> dict:
    r = _client.delete(path, **kwargs)
    r.raise_for_status()
    return r.json()
