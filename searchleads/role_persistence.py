"""Additive persistence boundary for evidence-backed ProfessionalRole records."""
from __future__ import annotations
from .domain import ProfessionalRole
from .persistence import MissingReferenceError, SQLiteLeadStore, _dump_provenance, _load_provenance

ROLE_SCHEMA_VERSION = 1

def ensure_professional_role_schema(store: SQLiteLeadStore) -> None:
    store._conn.executescript('''
        CREATE TABLE IF NOT EXISTS professional_roles (
            role_id TEXT PRIMARY KEY,
            person_id TEXT NOT NULL REFERENCES people(person_id),
            company_id TEXT NOT NULL REFERENCES companies(company_id),
            title TEXT NOT NULL,
            provenance TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_professional_roles_person_company
            ON professional_roles(person_id, company_id);
    ''')
    store._conn.commit()

def save_professional_role(store: SQLiteLeadStore, role: ProfessionalRole) -> None:
    ensure_professional_role_schema(store)
    if store.get_person(role.person_id) is None:
        raise MissingReferenceError(f"role person does not exist: {role.person_id}")
    if store.get_company(role.company_id) is None:
        raise MissingReferenceError(f"role company does not exist: {role.company_id}")
    store._assert_provenance_exists(role.provenance)
    store._insert_or_validate_same(
        table="professional_roles", id_column="role_id", identifier=role.role_id,
        columns=("role_id","person_id","company_id","title","provenance"),
        values=(role.role_id,role.person_id,role.company_id,role.title,_dump_provenance(role.provenance)),
    )

def get_professional_role(store: SQLiteLeadStore, role_id: str) -> ProfessionalRole | None:
    ensure_professional_role_schema(store)
    row=store._conn.execute("SELECT role_id, person_id, company_id, title, provenance FROM professional_roles WHERE role_id = ?",(role_id,)).fetchone()
    if row is None: return None
    return ProfessionalRole(row["role_id"],row["person_id"],row["company_id"],row["title"],_load_provenance(row["provenance"]))
