"""Root configuration for pytest."""

import argparse
import sys
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from fmu.datamodels.fmu_results import fields
from fmu.datamodels.fmu_results.enums import Classification
from fmu.datamodels.fmu_results.global_configuration import (
    Access,
    GlobalConfiguration,
    Stratigraphy,
    StratigraphyElement,
)
from pytest import MonkeyPatch

from fmu_settings_cli.__main__ import _parse_args
from fmu_settings_cli.init.main import REQUIRED_FMU_PROJECT_SUBDIRS


@pytest.fixture
def default_args() -> argparse.Namespace:
    """Returns default arguments when running `fmu-settings`."""
    with patch.object(sys, "argv", ["fmu", "settings"]):
        return _parse_args()


@pytest.fixture
def patch_ensure_port() -> Generator[None]:
    """Patches ensure port so tests can run if fmu-settings is running."""
    with patch("fmu_settings_cli.settings.main.ensure_port"):
        yield


@pytest.fixture
def in_tmp_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> Generator[Path]:
    """Monkeypatches into a tmp_path."""
    monkeypatch.chdir(tmp_path)
    yield tmp_path


@pytest.fixture
def in_fmu_project(in_tmp_path: Path, monkeypatch: MonkeyPatch) -> Generator[Path]:
    """Monkeypatches into a tmp_path with a 'valid' FMU project."""
    for dir_ in REQUIRED_FMU_PROJECT_SUBDIRS:
        (in_tmp_path / dir_).mkdir(parents=True, exist_ok=True)
    yield in_tmp_path


@pytest.fixture
def masterdata_dict() -> dict[str, Any]:
    """Example masterdata from SMDA."""
    return {
        "smda": {
            "country": [
                {
                    "identifier": "Norway",
                    "uuid": "ad214d85-8a1d-19da-e053-c918a4889309",
                }
            ],
            "discovery": [
                {
                    "short_identifier": "DROGON",
                    "uuid": "ad214d85-8a1d-19da-e053-c918a4889309",
                }
            ],
            "field": [
                {
                    "identifier": "DROGON",
                    "uuid": "ad214d85-8a1d-19da-e053-c918a4889309",
                }
            ],
            "coordinate_system": {
                "identifier": "ST_WGS84_UTM37N_P32637",
                "uuid": "ad214d85-dac7-19da-e053-c918a4889309",
            },
            "stratigraphic_column": {
                "identifier": "DROGON_HAS_NO_STRATCOLUMN",
                "uuid": "ad214d85-8a1d-19da-e053-c918a4889309",
            },
        }
    }


@pytest.fixture
def model_dict() -> dict[str, Any]:
    """Example model information."""
    return {
        "name": "Drogon",
        "revision": "21.0.0",
        "description": None,
    }


@pytest.fixture
def access_dict() -> dict[str, Any]:
    """Example access information."""
    return {
        "asset": {"name": "Drogon"},
        "classification": "internal",
    }


@pytest.fixture
def stratigraphy_dict() -> dict[str, Any]:
    """Example stratigraphy information."""
    return {
        "MSL": {
            "stratigraphic": False,
            "name": "MSL",
        },
        "Seabase": {
            "stratigraphic": False,
            "name": "Seabase",
        },
        "TopVolantis": {
            "stratigraphic": True,
            "name": "VOLANTIS GP. Top",
            "alias": ["TopVOLANTIS", "TOP_VOLANTIS"],
            "stratigraphic_alias": ["TopValysar", "Valysar Fm. Top"],
        },
        "TopTherys": {"stratigraphic": True, "name": "Therys Fm. Top"},
        "TopVolon": {"stratigraphic": True, "name": "Volon Fm. Top"},
        "BaseVolon": {"stratigraphic": True, "name": "Volon Fm. Base"},
        "BaseVolantis": {"stratigraphic": True, "name": "VOLANTIS GP. Base"},
        "Mantle": {"stratigraphic": False, "name": "Mantle"},
        "Above": {"stratigraphic": False, "name": "Above"},
        "Valysar": {"stratigraphic": True, "name": "Valysar Fm."},
        "Therys": {"stratigraphic": True, "name": "Therys Fm."},
        "Volon": {"stratigraphic": True, "name": "Volon Fm."},
        "Below": {"stratigraphic": False, "name": "Below"},
    }


@pytest.fixture
def global_variables_without_masterdata() -> dict[str, Any]:
    """Example global_variables.yml file without masterdata."""
    return {
        "global": {
            "dates": ["2018-01-01", "2018-07-01", "2019-07-01", "2020-07-01"],
        },
    }


@pytest.fixture
def global_variables_with_masterdata(
    masterdata_dict: dict[str, Any],
    access_dict: dict[str, Any],
    model_dict: dict[str, Any],
    stratigraphy_dict: dict[str, Any],
    global_variables_without_masterdata: dict[str, Any],
) -> dict[str, Any]:
    """Example global_variables.yml file with masterdata."""
    return {
        "masterdata": masterdata_dict,
        "access": access_dict,
        "model": model_dict,
        "stratigraphy": stratigraphy_dict,
        **global_variables_without_masterdata,
    }


@pytest.fixture
def generate_strict_valid_globalconfiguration() -> Callable[[], GlobalConfiguration]:
    """Generates a global configuration that is valid, but can switch particular models.

    All values are left empty by default.
    """

    def _generate_cfg(  # noqa: PLR0913
        *,
        classification: Classification | None = Classification.internal,
        asset: fields.Asset | None = None,
        coordinate_system: fields.CoordinateSystem | None = None,
        stratigraphic_column: fields.StratigraphicColumn | None = None,
        country_items: list[fields.CountryItem] | None = None,
        discovery_items: list[fields.DiscoveryItem] | None = None,
        field_items: list[fields.FieldItem] | None = None,
        model: fields.Model | None = None,
    ) -> GlobalConfiguration:
        return GlobalConfiguration(
            access=Access(
                asset=asset or fields.Asset(name=""), classification=classification
            ),
            masterdata=fields.Masterdata(
                smda=fields.Smda(
                    coordinate_system=(
                        coordinate_system
                        or fields.CoordinateSystem(identifier="", uuid=uuid4())
                    ),
                    stratigraphic_column=(
                        stratigraphic_column
                        or fields.StratigraphicColumn(identifier="", uuid=uuid4())
                    ),
                    country=country_items or [],
                    discovery=discovery_items or [],
                    field=field_items or [],
                )
            ),
            model=model or fields.Model(name="", revision=""),
            stratigraphy=Stratigraphy(
                {"MSL": StratigraphyElement(name="MSL", stratigraphic=False)}
            ),
        )

    return _generate_cfg
