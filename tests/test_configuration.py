from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_compose_reads_database_credentials_from_ignored_env_file():
    gitignore = (ROOT / ".gitignore").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()

    assert ".env" in gitignore
    assert "${POSTGRES_USER}" in compose
    assert "${POSTGRES_PASSWORD}" in compose
    assert "${POSTGRES_DB}" in compose
    assert "gameleaders:gameleaders" not in compose
