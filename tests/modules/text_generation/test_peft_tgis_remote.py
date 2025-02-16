"""Tests for prompt tuning based inference via TGIS backend; note that these tests mock the
TGIS client and do NOT actually start/hit a TGIS server instance.
"""
# Standard
from typing import Iterable
from unittest import mock
import os
import tempfile

# Third Party
import pytest

# Local
from caikit_nlp.modules.text_generation import PeftPromptTuningTGIS
from tests.fixtures import (
    StubTGISClient,
    causal_lm_dummy_model,
    causal_lm_train_kwargs,
    stub_tgis_backend,
)

SAMPLE_TEXT = "Hello stub"


def test_load_and_run(causal_lm_dummy_model, stub_tgis_backend):
    """Ensure we can export an in memory model, load it, and (mock) run it with the right text & prefix ID."""
    # Patch our stub backend into caikit so that we don't actually try to start TGIS
    causal_lm_dummy_model.verbalizer = "hello distributed {{input}}"

    with mock.patch.object(StubTGISClient, "Generate") as mock_gen:
        mock_gen.side_effect = StubTGISClient.unary_generate

        # Save the local model & reload it a TGIS backend distributed module
        # Also, save the name of the dir + prompt ID, which is the path TGIS expects for the prefix ID
        with tempfile.TemporaryDirectory() as model_dir:
            causal_lm_dummy_model.save(model_dir)
            mock_tgis_model = PeftPromptTuningTGIS.load(model_dir, stub_tgis_backend)
            model_prompt_dir = os.path.split(model_dir)[-1]

        # Run an inference request, which is wrapped around our mocked Generate call
        result = mock_tgis_model.run(SAMPLE_TEXT, preserve_input_text=True)
        StubTGISClient.validate_unary_generate_response(result)

        stub_generation_request = mock_gen.call_args_list[0].args[0]

        # Validate that our verbalizer carried over correctly & was applied at inference time
        assert mock_tgis_model.verbalizer == causal_lm_dummy_model.verbalizer
        assert stub_generation_request.requests[
            0
        ].text == "hello distributed {}".format(SAMPLE_TEXT)

        # Ensure that our prefix ID matches the expected path based on our tmpdir and config
        assert model_prompt_dir == stub_generation_request.prefix_id


def test_load_and_run_stream_out(causal_lm_dummy_model, stub_tgis_backend):
    """Ensure we can export an in memory model, load it, and (mock) run output streaming
    with the right text & prefix ID."""
    # Patch our stub backend into caikit so that we don't actually try to start TGIS
    causal_lm_dummy_model.verbalizer = "hello distributed {{input}}"

    with mock.patch.object(StubTGISClient, "GenerateStream") as mock_gen:
        mock_gen.side_effect = StubTGISClient.stream_generate

        # Save the local model & reload it a TGIS backend distributed module
        # Also, save the name of the dir + prompt ID, which is the path TGIS expects for the prefix ID
        with tempfile.TemporaryDirectory() as model_dir:
            causal_lm_dummy_model.save(model_dir)
            mock_tgis_model = PeftPromptTuningTGIS.load(model_dir, stub_tgis_backend)
            model_prompt_dir = os.path.split(model_dir)[-1]
            assert stub_tgis_backend.load_prompt_artifacts.called_once()

        # Run an inference request, which is wrapped around our mocked GenerateStream call
        stream_result = mock_tgis_model.run_stream_out(
            SAMPLE_TEXT, preserve_input_text=True
        )
        StubTGISClient.validate_stream_generate_response(stream_result)

        stub_generation_request = mock_gen.call_args_list[0].args[0]

        # Validate that our verbalizer carried over correctly & was applied at inference time
        assert mock_tgis_model.verbalizer == causal_lm_dummy_model.verbalizer
        assert stub_generation_request.request.text == "hello distributed {}".format(
            SAMPLE_TEXT
        )

        # Ensure that our prefix ID matches the expected path based on our tmpdir and config
        assert model_prompt_dir == stub_generation_request.prefix_id
