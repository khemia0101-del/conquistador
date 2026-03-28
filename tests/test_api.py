"""Tests for API configuration and models."""

import pytest
from conquistador.config import Settings
from conquistador.comms.sms import CARRIER_GATEWAYS
from conquistador.quality.vetting import check_vetting_completeness, VETTING_REQUIREMENTS
from conquistador.web.auth import hash_password, verify_password


class TestConfig:
    def test_default_settings(self):
        settings = Settings()
        assert settings.ai_provider == "nvidia"
        assert settings.ai_model == "meta/llama-3.1-70b-instruct"
        assert settings.business_phone == "717-397-9800"

    def test_service_zips_populated(self):
        settings = Settings()
        assert len(settings.service_zips) > 0
        assert "17602" in settings.service_zips  # Lancaster
        assert "17401" in settings.service_zips  # York
        assert "17101" in settings.service_zips  # Harrisburg


class TestCarrierGateways:
    def test_all_major_carriers(self):
        assert "verizon" in CARRIER_GATEWAYS
        assert "att" in CARRIER_GATEWAYS
        assert "tmobile" in CARRIER_GATEWAYS
        assert "sprint" in CARRIER_GATEWAYS

    def test_gateway_format(self):
        for carrier, gateway in CARRIER_GATEWAYS.items():
            assert gateway.startswith("@"), f"Gateway for {carrier} should start with @"
            assert ".com" in gateway or ".net" in gateway


class TestVetting:
    def test_complete_data_passes(self):
        data = {
            "license_number": "PA-12345",
            "insurance_verified": True,
            "service_types": ["hvac_repair"],
            "service_zips": ["17602"],
            "phone": "7175551234",
        }
        missing = check_vetting_completeness(data)
        assert len(missing) == 0

    def test_missing_license(self):
        data = {
            "insurance_verified": True,
            "service_types": ["hvac_repair"],
            "service_zips": ["17602"],
            "phone": "7175551234",
        }
        missing = check_vetting_completeness(data)
        assert any("license" in m.lower() for m in missing)

    def test_empty_data(self):
        missing = check_vetting_completeness({})
        assert len(missing) > 0


class TestAuth:
    def test_password_hashing(self):
        password = "testpassword123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)
