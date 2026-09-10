import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_config_service import LLMConfigService, LLMRuntimeConfig
from app.services.llm_service import LLMService
from app.services.prompt_config_service import DEFAULT_PROMPTS, PromptConfigService


def test_llm_config_service_validation_and_persistence(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("app.services.llm_config_service.settings.openai_api_key", "")
    config_file = tmp_path / "llm-config.json"
    service = LLMConfigService(config_file)

    # Initially defaults to fallback
    initial = service.runtime_config()
    assert isinstance(initial, LLMRuntimeConfig)

    # Validation: invalid base_url
    with pytest.raises(ValueError, match="llm_base_url_invalid"):
        service.save(
            enabled=True,
            base_url="not-a-url",
            model="gpt-4o",
            api_key="sk-test-key-12345",
        )

    # Validation: missing model
    with pytest.raises(ValueError, match="llm_model_required"):
        service.save(
            enabled=True,
            base_url="https://api.openai.com/v1",
            model="",
            api_key="sk-test-key-12345",
        )

    # Validation: missing api_key
    with pytest.raises(ValueError, match="llm_api_key_required"):
        service.save(
            enabled=True,
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
            api_key="",
        )

    # Valid save
    saved = service.save(
        enabled=True,
        base_url="https://api.openai.com/v1/",
        model="gpt-4o",
        api_key="sk-secret-12345678",
    )
    assert saved["enabled"] is True
    assert saved["base_url"] == "https://api.openai.com/v1"
    assert saved["model"] == "gpt-4o"
    assert saved["has_api_key"] is True
    assert "sk-" in str(saved["api_key_masked"])
    assert "secret" not in str(saved["api_key_masked"])

    # Verify cached reading & persisted file
    reloaded = service.runtime_config()
    assert reloaded.enabled is True
    assert reloaded.base_url == "https://api.openai.com/v1"
    assert reloaded.model == "gpt-4o"
    assert reloaded.api_key == "sk-secret-12345678"

    # Saving with empty api_key preserves the existing key
    updated = service.save(
        enabled=True,
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        api_key="",
    )
    assert updated["model"] == "gpt-4o-mini"
    assert service.runtime_config().api_key == "sk-secret-12345678"


def test_llm_service_enabled_requires_model(tmp_path: Path, monkeypatch):
    config_file = tmp_path / "llm-config.json"
    custom_config = LLMConfigService(config_file)
    monkeypatch.setattr("app.services.llm_service.llm_config_service", custom_config)

    llm = LLMService()

    # When model is empty string, enabled must be False
    config_file.write_text(
        json.dumps({
            "enabled": True,
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test",
            "model": "",
        }),
        encoding="utf-8",
    )
    custom_config._cached_mtime = None
    assert llm.enabled is False

    # When model is present, enabled is True
    config_file.write_text(
        json.dumps({
            "enabled": True,
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test",
            "model": "gpt-4o",
        }),
        encoding="utf-8",
    )
    custom_config._cached_mtime = None
    assert llm.enabled is True


def test_prompt_config_service_lifecycle_and_switching(tmp_path: Path):
    prompt_file = tmp_path / "prompt-versions.json"
    service = PromptConfigService(prompt_file)

    # Initial state
    state = service.public_state()
    assert state["active_version"] == 1
    assert state["selected_version"] == 1
    assert len(state["versions"]) == 1
    assert "behavior_system" in state["prompts"]

    # Create version 2 with customized prompt
    new_prompts = dict(state["prompts"])
    new_prompts["reply_system"] = "自定义回复系统提示词 [[character_name]]"
    created = service.create_version("测试新版", new_prompts, activate=True)
    assert created["active_version"] == 2
    assert created["selected_version"] == 2
    assert len(created["versions"]) == 2

    # Render uses active version (v2)
    rendered = service.render("reply_system", {"character_name": "苏禾"})
    assert rendered == "自定义回复系统提示词 苏禾"

    # Switch back to version 1
    activated = service.activate(1)
    assert activated["active_version"] == 1
    # Render now uses v1
    rendered_v1 = service.render("reply_system", {
        "character_name": "苏禾",
        "profile_json": "{}",
        "relationship_json": "{}",
        "emotion_json": "{}",
        "scene_json": "{}",
        "decision_json": "{}",
    })
    assert "你是角色“苏禾”" in rendered_v1

    # Inactive version query
    v2_state = service.public_state(selected_version=2)
    assert v2_state["active_version"] == 1
    assert v2_state["selected_version"] == 2
    assert v2_state["prompts"]["reply_system"] == "自定义回复系统提示词 [[character_name]]"


def test_prompt_render_anti_injection_and_fallback(tmp_path: Path):
    prompt_file = tmp_path / "prompt-versions.json"
    service = PromptConfigService(prompt_file)

    # Test variable replacement prevents secondary injection
    # If user message contains [[character_name]], it should NOT be replaced by character_name
    template_prompts = dict(DEFAULT_PROMPTS)
    template_prompts["reply_user"] = "消息：[[user_message]]；角色：[[character_name]]"
    service.create_version("测试注入", template_prompts, activate=True)

    rendered = service.render("reply_user", {
        "user_message": "我是 [[character_name]] 吗？",
        "character_name": "林晚",
    })
    # The user_message should retain the literal '[[character_name]]' and not turn into '林晚'
    assert rendered == "消息：我是 [[character_name]] 吗？；角色：林晚"

    # Test corrupted active_version self-healing
    corrupted = {
        "active_version": 99999,
        "versions": [
            {
                "version": 1,
                "name": "v1",
                "created_at": "2026-01-01T00:00:00Z",
                "prompts": DEFAULT_PROMPTS,
            }
        ],
    }
    prompt_file.write_text(json.dumps(corrupted), encoding="utf-8")
    # Reset in-memory cache to force read
    service._cached_mtime = None
    service._cached_state = None

    # Should gracefully auto-heal to version 1 without raising
    state = service.public_state()
    assert state["active_version"] == 1
    rendered_fallback = service.render("behavior_system", {"character_name": "沈言", "profile_json": "{}"})
    assert "沈言" in rendered_fallback


def test_admin_settings_api_endpoints():
    client = TestClient(app)

    # 1. GET chat-model
    resp = client.get("/api/admin/settings/chat-model")
    assert resp.status_code == 200
    data = resp.json()
    assert "enabled" in data
    assert "base_url" in data
    assert "model" in data
    assert "has_api_key" in data

    # 2. PUT chat-model validation
    resp_invalid = client.put(
        "/api/admin/settings/chat-model",
        json={"enabled": True, "base_url": "invalid_url", "model": "gpt-4o", "api_key": "test"},
    )
    assert resp_invalid.status_code == 422

    # 3. GET prompts
    resp_prompts = client.get("/api/admin/settings/prompts")
    assert resp_prompts.status_code == 200
    prompts_data = resp_prompts.json()
    assert "active_version" in prompts_data
    assert "versions" in prompts_data
    assert "prompts" in prompts_data

    # 4. PUT activate non-existent version returns 404
    resp_404 = client.put("/api/admin/settings/prompts/versions/99999/activate")
    assert resp_404.status_code == 404

    # 5. PUT activate invalid negative version returns 422
    resp_422 = client.put("/api/admin/settings/prompts/versions/-1/activate")
    assert resp_422.status_code == 422