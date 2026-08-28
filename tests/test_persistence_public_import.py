from searchleads.persistence import SQLiteRepository, SemanticReferenceError
from searchleads.persistence.semantic import SQLiteRepository as SemanticSQLiteRepository


def test_public_sqlite_repository_is_semantic_repository() -> None:
    assert SQLiteRepository is SemanticSQLiteRepository
    assert issubclass(SemanticReferenceError, RuntimeError)
