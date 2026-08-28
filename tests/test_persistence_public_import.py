from searchleads.persistence import SQLiteRepository, SemanticReferenceError
from searchleads.persistence.ledger import SQLiteRepository as LedgerSQLiteRepository
from searchleads.persistence.semantic import SQLiteRepository as SemanticSQLiteRepository


def test_public_sqlite_repository_layers_semantic_and_ledger_checks() -> None:
    assert SQLiteRepository is LedgerSQLiteRepository
    assert issubclass(SQLiteRepository, SemanticSQLiteRepository)
    assert issubclass(SemanticReferenceError, RuntimeError)
