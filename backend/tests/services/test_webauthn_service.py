"""webauthn_service 单元测试。"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.webauthn_service import (
    begin_authentication,
    begin_registration,
    complete_authentication,
    complete_registration,
)


def _make_fake_user():
    """创建一个模拟 User 对象。"""
    user = SimpleNamespace()
    user.id = 42
    user.tg_username = "test_user"
    user.email = "test@example.com"
    return user


def _make_fake_credential():
    """创建一个模拟 WebAuthnCredential 对象。"""
    cred = SimpleNamespace()
    cred.credential_id = "dGVzdC1jcmVkLWlk"  # base64url of "test-cred-id"
    cred.public_key = "dGVzdC1wdWJsaWMta2V5"  # base64url of "test-public-key"
    cred.sign_count = 5
    return cred


@patch("app.services.webauthn_service.webauthn")
async def test_begin_registration(mock_webauthn):
    """begin_registration 应返回 (options_dict, challenge_b64url)。"""
    fake_options = MagicMock()
    fake_options.challenge = b"test-challenge-bytes"
    mock_webauthn.generate_registration_options.return_value = fake_options
    mock_webauthn.options_to_json.return_value = json.dumps(
        {"rp": {"name": "Test"}, "challenge": "abc"}
    )

    user = _make_fake_user()
    options_dict, challenge_b64 = begin_registration(user)

    mock_webauthn.generate_registration_options.assert_called_once()
    assert isinstance(options_dict, dict)
    assert isinstance(challenge_b64, str)
    assert len(challenge_b64) > 0


@patch("app.services.webauthn_service.webauthn")
async def test_complete_registration(mock_webauthn):
    """complete_registration 应返回 (cred_id_b64, pub_key_b64, sign_count)。"""
    fake_verification = MagicMock()
    fake_verification.credential_id = b"cred-id-bytes"
    fake_verification.credential_public_key = b"pub-key-bytes"
    fake_verification.sign_count = 1
    mock_webauthn.verify_registration_response.return_value = fake_verification

    response_json = {"id": "test", "response": {}}
    cred_id, pub_key, sign_count = complete_registration(
        response_json, challenge_b64="dGVzdC1jaGFsbGVuZ2U"
    )

    mock_webauthn.verify_registration_response.assert_called_once()
    assert isinstance(cred_id, str)
    assert isinstance(pub_key, str)
    assert sign_count == 1


@patch("app.services.webauthn_service.webauthn")
async def test_begin_authentication(mock_webauthn):
    """begin_authentication 应返回 (options_dict, challenge_b64url)。"""
    fake_options = MagicMock()
    fake_options.challenge = b"auth-challenge-bytes"
    mock_webauthn.generate_authentication_options.return_value = fake_options
    mock_webauthn.options_to_json.return_value = json.dumps(
        {"challenge": "xyz", "allowCredentials": []}
    )

    cred = _make_fake_credential()
    options_dict, challenge_b64 = begin_authentication([cred])

    mock_webauthn.generate_authentication_options.assert_called_once()
    assert isinstance(options_dict, dict)
    assert isinstance(challenge_b64, str)


@patch("app.services.webauthn_service.webauthn")
async def test_complete_authentication(mock_webauthn):
    """complete_authentication 应返回新的 sign_count。"""
    fake_verification = MagicMock()
    fake_verification.new_sign_count = 6
    mock_webauthn.verify_authentication_response.return_value = fake_verification

    cred = _make_fake_credential()
    response_json = {"id": "test", "response": {}}
    new_sign_count = complete_authentication(
        response_json, credential=cred, challenge_b64="dGVzdC1jaGFsbGVuZ2U"
    )

    mock_webauthn.verify_authentication_response.assert_called_once()
    assert new_sign_count == 6
