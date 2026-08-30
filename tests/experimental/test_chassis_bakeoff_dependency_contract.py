from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import pytest

for package in ("followthemoney", "nomenklatura", "crawlee", "rigour", "python-stdnum"):
    try:
        version(package)
    except PackageNotFoundError:
        pytest.skip("external chassis dependencies are installed only in the bake-off workflow", allow_module_level=True)


EXPECTED = {
    "followthemoney": "4.10.2",
    "nomenklatura": "4.14.0",
    "crawlee": "1.9.3",
    "rigour": "2.3.1",
    "python-stdnum": "2.2",
}


def test_bakeoff_dependency_versions_are_exact_and_reproducible() -> None:
    installed = {package: version(package) for package in EXPECTED}
    assert installed == EXPECTED

    print("CHASSIS_DEPENDENCY_CONTRACT_V1")
    for package, installed_version in installed.items():
        print(f"{package}={installed_version}")
    print("dependency_resolution_is_part_of_experiment=YES")


def test_nomenklatura_rigour_pair_matches_declared_supported_range() -> None:
    # Nomenklatura 4.14.0 declares rigour >=2.2.3,<3.0.0. This test makes the
    # chosen point in that supported range explicit rather than allowing pip to
    # choose a different Rigour build on a later date.
    assert version("nomenklatura") == "4.14.0"
    assert version("rigour") == "2.3.1"


def test_rigour_cnpj_dependency_is_the_release_with_alphanumeric_support() -> None:
    # python-stdnum 2.2 release notes and stdnum.br.cnpj implementation add the
    # July-2026 alphanumeric Brazilian CNPJ format. The functional CNPJ bake-off
    # separately checks it against the Receita/Serpro oracle.
    assert version("python-stdnum") == "2.2"
