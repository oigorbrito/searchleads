from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import pytest

try:
    version("yente")
except PackageNotFoundError:
    pytest.skip("Yente is installed only in its isolated bake-off job", allow_module_level=True)

from fastapi import APIRouter
from yente import settings
from yente.app import create_app


YENTE_STABLE_DEPENDENCIES = {
    "yente": "5.5.0",
    "followthemoney": "4.9.2",
    "nomenklatura": "4.10.0",
    "rigour": "2.1.2",
}


def _paths() -> set[str]:
    app = create_app()
    return {route.path for route in app.routes}


def test_yente_stable_application_dependency_generation_is_explicit() -> None:
    installed = {package: version(package) for package in YENTE_STABLE_DEPENDENCIES}
    assert installed == YENTE_STABLE_DEPENDENCIES

    print("YENTE_STABLE_DEPENDENCY_GENERATION_V1")
    for package, installed_version in installed.items():
        print(f"{package}={installed_version}")
    print("latest_core_bakeoff_stack_is_intentionally_separate=YES")
    print("reason=yente_5_5_0_pins_older_ftm_nomenklatura_rigour")


def test_yente_exposes_a_real_application_chassis_without_starting_external_services() -> None:
    paths = _paths()
    required = {
        "/match/{dataset}",
        "/search/{dataset}",
        "/healthz",
        "/readyz",
        "/catalog",
        "/algorithms",
        "/openapi.json",
    }
    assert required <= paths

    print("YENTE_APPLICATION_SURFACE_V1")
    print(f"routes_total={len(paths)}")
    for path in sorted(required):
        print(f"required_route={path} present=YES")
    print("external_index_connection_started=NO")
    print("lifespan_started=NO")


def test_yente_has_bounded_match_and_api_limits_as_native_configuration() -> None:
    assert settings.MAX_BATCH == 100
    assert settings.MAX_MATCHES == 500
    assert settings.MAX_MATCH_CANDIDATES == 500
    assert settings.MAX_PAGE == 500
    assert settings.MAX_URL_LENGTH == 60000
    assert settings.VERIFY_CHECKSUM is True

    print("YENTE_NATIVE_BOUNDS_V1")
    print(f"max_batch={settings.MAX_BATCH}")
    print(f"max_matches={settings.MAX_MATCHES}")
    print(f"max_match_candidates={settings.MAX_MATCH_CANDIDATES}")
    print(f"max_page={settings.MAX_PAGE}")
    print(f"max_url_length={settings.MAX_URL_LENGTH}")
    print(f"verify_checksum={int(settings.VERIFY_CHECKSUM)}")


def test_searchleads_routes_can_be_added_without_modifying_yente_source() -> None:
    app = create_app()
    before = {route.path for route in app.routes}

    router = APIRouter(prefix="/searchleads")

    @router.get("/qualification-contract-probe")
    async def qualification_contract_probe() -> dict[str, str]:
        return {"authority": "searchleads"}

    app.include_router(router)
    after = {route.path for route in app.routes}

    assert "/searchleads/qualification-contract-probe" not in before
    assert "/searchleads/qualification-contract-probe" in after
    assert before < after

    print("YENTE_EXTENSION_SURFACE_V1")
    print("additive_searchleads_router_without_upstream_patch=YES")
    print("proof_scope=FastAPI_extension_surface_only")
    print("domain_model_and_persistence_fit=NOT_PROVEN_BY_THIS_TEST")


def test_yente_full_chassis_constraints_are_not_hidden() -> None:
    # These are architecture constraints from the stable Yente configuration,
    # not reasons to reject the chassis automatically. They belong in the cost
    # side of the bake-off.
    assert settings.INDEX_TYPE in {"elasticsearch", "opensearch"}
    assert settings.INDEX_URL

    print("YENTE_FULL_CHASSIS_CONSTRAINTS_V1")
    print(f"search_index_type={settings.INDEX_TYPE}")
    print("external_search_service_required=YES")
    print("general_api_auth_access_control=NATIVE_NO (per Yente service contract)")
    print("searchleads_contact_qualification_campaign_domain=NATIVE_NO")
    print("upstream_match_search_screening_domain=NATIVE_YES")
