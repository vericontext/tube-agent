"""Tests for report API endpoints."""


class _Settings:
    gemini_api_key = "gemini-test-key"


def test_generate_channel_overview(seeded_client, seeded_storage, monkeypatch):
    from tube_agent.api.routes import reports as reports_route

    def _fake_report(channel_id, handle, storage, gemini_client):
        storage.save_report(channel_id, "channel_overview", "# Channel overview\n\nStart here.")
        return "# Channel overview\n\nStart here."

    monkeypatch.setattr(reports_route, "get_settings", lambda: _Settings())
    monkeypatch.setattr(reports_route, "GeminiClient", lambda key: object())
    monkeypatch.setattr(reports_route, "generate_channel_report", _fake_report)

    resp = seeded_client.post("/api/v1/channels/testchannel/reports/channel_overview")

    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "channel_overview"
    assert "Start here" in data["content_md"]


def test_get_report_after_generation(seeded_client, seeded_storage):
    seeded_storage.save_report("UC_test123", "channel_overview", "# Existing overview")

    resp = seeded_client.get("/api/v1/channels/testchannel/reports/channel_overview")

    assert resp.status_code == 200
    assert resp.json()["content_md"] == "# Existing overview"
