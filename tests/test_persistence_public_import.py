from searchleads.persistence import SQLiteRepository, SemanticReferenceError
from searchleads.persistence.identity import SQLiteRepository as IdentitySQLiteRepository
from searchleads.persistence.ledger import SQLiteRepository as LedgerSQLiteRepository
from searchleads.persistence.semantic import SQLiteRepository as SemanticSQLiteRepository
from searchleads.persistence.v3 import SQLiteRepository as V3SQLiteRepository


def test_public_sqlite_repository_layers_identity_v3_ledger_and_semantic_checks() -> None:
    assert SQLiteRepository is IdentitySQLiteRepository
    assert issubclass(SQLiteRepository, V3SQLiteRepository)
    assert issubclass(V3SQLiteRepository, LedgerSQLiteRepository)
    assert issubclass(LedgerSQLiteRepository, SemanticSQLiteRepository)
    assert issubclass(SemanticReferenceError, RuntimeError)
