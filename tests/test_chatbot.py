"""Tests for chatbot functionality."""

import json
import pytest
from conquistador.chatbot.extractor import lead_complete, extract_lead_data
from conquistador.chatbot.prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT
from conquistador.agents.intake_agent import calculate_lead_score


class TestLeadComplete:
    def test_empty_conversation(self):
        assert lead_complete([]) is False

    def test_incomplete_conversation(self):
        conv = [
            {"role": "user", "content": "I need heating oil"},
            {"role": "assistant", "content": "What is your zip code?"},
        ]
        assert lead_complete(conv) is False

    def test_complete_conversation(self):
        conv = [
            {"role": "assistant", "content": "Thank you! A contractor will reach out. [LEAD_COMPLETE]"},
        ]
        assert lead_complete(conv) is True


class TestLeadScoring:
    def test_emergency_high_score(self):
        data = {
            "urgency": "emergency",
            "service_type": "emergency",
            "phone": "7175551234",
            "email": "test@test.com",
            "address": "123 Main St",
        }
        score = calculate_lead_score(data)
        assert score >= 70

    def test_routine_lower_score(self):
        data = {
            "urgency": "routine",
            "service_type": "furnace_maintenance",
            "phone": "7175551234",
        }
        score = calculate_lead_score(data)
        assert score < 60

    def test_score_capped_at_100(self):
        data = {
            "urgency": "emergency",
            "service_type": "emergency",
            "phone": "7175551234",
            "email": "test@test.com",
            "address": "123 Main St",
        }
        score = calculate_lead_score(data)
        assert score <= 100


class TestSystemPrompt:
    def test_prompt_contains_steps(self):
        assert "STEP 1" in SYSTEM_PROMPT
        assert "STEP 6" in SYSTEM_PROMPT

    def test_prompt_contains_valid_zips(self):
        assert "17601" in SYSTEM_PROMPT
        assert "17401" in SYSTEM_PROMPT

    def test_extraction_prompt_has_json(self):
        assert '"name"' in EXTRACTION_PROMPT
        assert '"phone"' in EXTRACTION_PROMPT
        assert '"service_type"' in EXTRACTION_PROMPT
