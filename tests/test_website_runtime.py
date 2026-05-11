from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from src.config import clear_settings_cache

    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture
def client(tmp_path, monkeypatch):
    import src.api.main as main

    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text(
        '<!doctype html><html><head></head><body><div id="root">MeetAstro</div></body></html>',
        encoding="utf-8",
    )
    (assets_dir / "index-abcd1234.js").write_text("console.log('ok')", encoding="utf-8")

    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()

    monkeypatch.setattr(main, "WEB_STATIC_DIR", dist_dir)
    monkeypatch.setattr(main, "DOWNLOAD_DIR", downloads_dir)
    monkeypatch.setenv("APP_DOWNLOAD_FILENAME", "MeetAstro-Setup.msi")
    monkeypatch.setenv("APP_DOWNLOAD_VERSION", "1.2.3")
    monkeypatch.setenv("APP_DOWNLOAD_SIZE", "42 MB")

    return TestClient(main.create_app())


def test_root_serves_website_index_with_no_cache(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "MeetAstro" in response.text
    assert response.headers["cache-control"] == "no-cache"


def test_spa_route_serves_website_index(client):
    response = client.get("/features/deep-link")

    assert response.status_code == 200
    assert "MeetAstro" in response.text


def test_vite_asset_uses_immutable_cache(client):
    response = client.get("/assets/index-abcd1234.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_api_and_docs_routes_are_not_swallowed(client):
    health = client.get("/api/v1/health")
    unknown_api = client.get("/api/v1/not-real")
    docs = client.get("/docs")
    openapi = client.get("/openapi.json")

    assert health.status_code == 200
    assert unknown_api.status_code == 404
    assert unknown_api.headers["content-type"].startswith("application/json")
    assert docs.status_code == 200
    assert openapi.status_code == 200


def test_download_metadata_uses_env_and_missing_file_status(client):
    response = client.get("/downloads/metadata.json")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"
    assert response.json() == {
        "available": False,
        "url": "",
        "filename": "MeetAstro-Setup.msi",
        "version": "1.2.3",
        "size": "42 MB",
        "platform": "Windows",
    }


def test_download_windows_missing_msi_returns_404_json(client):
    response = client.get("/downloads/windows")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "Windows installer is not published."


def test_download_windows_serves_msi_attachment(client, tmp_path):
    import src.api.main as main

    msi_path = main.DOWNLOAD_DIR / "MeetAstro-Setup.msi"
    msi_path.write_bytes(b"msi")

    response = client.get("/downloads/windows")

    assert response.status_code == 200
    assert response.content == b"msi"
    assert response.headers["content-type"].startswith("application/x-msi")
    assert 'filename="MeetAstro-Setup.msi"' in response.headers["content-disposition"]


def test_download_filename_path_traversal_is_rejected(client, monkeypatch):
    from src.config import clear_settings_cache

    monkeypatch.setenv("APP_DOWNLOAD_FILENAME", "../bad.msi")
    clear_settings_cache()

    response = client.get("/downloads/windows")

    assert response.status_code == 404
    assert response.json()["detail"] == "Windows installer is not published."
