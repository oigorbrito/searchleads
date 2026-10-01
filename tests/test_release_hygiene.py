from searchleads.release_hygiene import (
    assess_repository_hygiene,
    assess_tracked_filenames,
)


def test_repository_hygiene_accepts_clean_production_source() -> None:
    assessment = assess_repository_hygiene(
        {
            "src/searchleads/example.py": "from __future__ import annotations\nVALUE = 1\n",
            "docs/example.md": "mentions crawlee as optional experimental breadth",
        }
    )

    assert assessment.ready
    assert assessment.violations == ()


def test_repository_hygiene_blocks_direct_send_path() -> None:
    assessment = assess_repository_hygiene(
        {"src/searchleads/mailer.py": "import smtplib\n"}
    )

    assert not assessment.ready
    assert assessment.violations[0].code == "DIRECT_SEND_PATH"
    assert assessment.violations[0].path == "src/searchleads/mailer.py"


def test_repository_hygiene_blocks_experimental_dependency_in_production() -> None:
    assessment = assess_repository_hygiene(
        {"src/searchleads/runtime.py": "from crawlee import Request\n"}
    )

    assert not assessment.ready
    assert assessment.violations[0].code == "EXPERIMENTAL_DEPENDENCY_IN_PRODUCTION"


def test_repository_hygiene_detects_strong_secret_without_echoing_value() -> None:
    secret = "ghp_" + "A" * 36
    assessment = assess_repository_hygiene(
        {"config.txt": f"TOKEN={secret}\n"}
    )

    assert not assessment.ready
    violation = assessment.violations[0]
    assert violation.code == "STRONG_SECRET_PATTERN"
    assert secret not in violation.detail
    assert "GITHUB_CLASSIC_PAT" in violation.detail


def test_repository_hygiene_detects_apify_and_openai_secrets_without_echoing_values() -> None:
    apify_secret = "apify_api_" + "x" * 32
    openai_secret = "sk-proj-" + "y" * 32
    assessment = assess_repository_hygiene(
        {
            "config.env": f"APIFY_TOKEN={apify_secret}\nOPENAI_KEY={openai_secret}\n"
        }
    )

    assert not assessment.ready
    patterns_found = {v.detail for v in assessment.violations}
    assert apify_secret not in str(patterns_found)
    assert openai_secret not in str(patterns_found)
    assert any("APIFY_API_TOKEN" in d for d in patterns_found)
    assert any("OPENAI_API_KEY" in d for d in patterns_found)


def test_tracked_filename_hygiene_blocks_runtime_artifacts() -> None:
    assessment = assess_tracked_filenames(
        (
            "src/searchleads/__init__.py",
            ".env",
            "var/searchleads.sqlite",
            "src/searchleads/__pycache__/module.pyc",
        )
    )

    assert not assessment.ready
    assert {item.path for item in assessment.violations} == {
        ".env",
        "var/searchleads.sqlite",
        "src/searchleads/__pycache__/module.pyc",
    }
