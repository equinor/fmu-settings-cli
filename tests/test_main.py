"""Tests for the __main__ module."""

from unittest import mock

from fmu.settings.cli import __main__


def test_main_invocation_with_no_options() -> None:
    """Tests that fmu-settings calls 'start_api_and_gui'."""
    with mock.patch(
        "fmu.settings.cli.__main__.start_api_and_gui"
    ) as mock_start_api_and_gui:
        __main__.main([])
        mock_start_api_and_gui.assert_called_once()


def test_main_invocation_with_api_subcommand() -> None:
    """Tests that fmu-settings calls 'start_api_and_gui'."""
    with mock.patch(
        "fmu.settings.cli.__main__.start_api_server"
    ) as mock_start_api_server:
        __main__.main(["api"])
        mock_start_api_server.assert_called_once()


def test_main_invocation_with_gui_subcommand() -> None:
    """Tests that fmu-settings calls 'start_api_and_gui'."""
    with mock.patch(
        "fmu.settings.cli.__main__.start_gui_server"
    ) as mock_start_gui_server:
        __main__.main(["gui"])
        mock_start_gui_server.assert_called_once()
