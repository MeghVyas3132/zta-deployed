from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import (
    Claim,
    ClaimSensitivity,
    Tenant,
    TenantStatus,
)


BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATHS = {
    "hd": BASE_DIR / "hd2024.csv",
    "ic": BASE_DIR / "ic2024.csv",
    "ef2024a": BASE_DIR / "ef2024a.csv",
    "efia2024": BASE_DIR / "efia2024.csv",
}

IPEDS_TENANT_ID = "33333333-3333-3333-3333-333333333333"


@dataclass(frozen=True)
class IpedInstitution:
    unitid: str
    name: str
    city: str
    state: str
    website: str
    open_admissions_flag: int
    total_enrollment: float
    total_fte: float
    graduate_mix_delta: float


def _csv_exists() -> bool:
    return all(path.exists() for path in CSV_PATHS.values())


def _safe_float(value: str | None) -> float:
    if value is None:
        return 0.0

    cleaned = value.strip()
    if not cleaned or cleaned in {"A", "B", "G", "R", "-1", "-2"}:
        return 0.0

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _safe_int(value: str | None) -> int:
    return int(_safe_float(value))


def _load_rows_by_unitid(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return {row["UNITID"]: row for row in reader if row.get("UNITID")}


def _load_fall_enrollment_rows(path: Path) -> dict[str, dict[str, str]]:
    preferred = [("1", "1"), ("99", "1"), ("29", "3"), ("14", "1")]
    ranked: dict[str, tuple[int, dict[str, str]]] = {}

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            unitid = row.get("UNITID")
            if not unitid:
                continue

            signature = (row.get("LINE", ""), row.get("SECTION", ""))
            if signature not in preferred:
                continue

            rank = preferred.index(signature)
            current = ranked.get(unitid)
            if current is None or rank < current[0]:
                ranked[unitid] = (rank, row)

    return {unitid: row for unitid, (_rank, row) in ranked.items()}


def _build_institutions() -> list[IpedInstitution]:
    hd_rows = _load_rows_by_unitid(CSV_PATHS["hd"])
    ic_rows = _load_rows_by_unitid(CSV_PATHS["ic"])
    efia_rows = _load_rows_by_unitid(CSV_PATHS["efia2024"])
    ef_rows = _load_fall_enrollment_rows(CSV_PATHS["ef2024a"])

    institutions: list[IpedInstitution] = []
    for unitid in sorted(set(hd_rows) & set(ic_rows) & set(efia_rows) & set(ef_rows)):
        hd = hd_rows[unitid]
        ic = ic_rows[unitid]
        efia = efia_rows[unitid]
        ef = ef_rows[unitid]

        undergrad_fte = _safe_float(efia.get("EFTEUG"))
        graduate_fte = _safe_float(efia.get("EFTEGD")) + _safe_float(efia.get("FTEDPP"))
        total_fte = undergrad_fte + graduate_fte
        total_enrollment = _safe_float(ef.get("EFTOTLT"))
        if total_fte <= 0 or total_enrollment <= 0:
            continue

        graduate_mix_delta = round(((graduate_fte - undergrad_fte) / max(total_fte, 1.0)) * 100, 2)

        institutions.append(
            IpedInstitution(
                unitid=unitid,
                name=hd.get("INSTNM", f"Institution {unitid}").strip(),
                city=hd.get("CITY", "").strip(),
                state=hd.get("STABBR", "").strip(),
                website=hd.get("WEBADDR", "").strip(),
                open_admissions_flag=1 if ic.get("OPENADMP") == "1" else 0,
                total_enrollment=total_enrollment,
                total_fte=round(total_fte, 2),
                graduate_mix_delta=graduate_mix_delta,
            )
        )

    return institutions


def _seed_tenant(db: Session) -> None:
    tenant = Tenant(
        id=IPEDS_TENANT_ID,
        name="IPEDS CSV Claims Tenant",
        domain="ipeds.local",
        subdomain="ipeds",
        status=TenantStatus.active,
        google_workspace_domain=None,
    )
    db.add(tenant)


def _build_claims(institutions: list[IpedInstitution]) -> list[Claim]:
    claims: list[Claim] = []
    for institution in institutions:
        entity_id = f"ipeds-{institution.unitid}"
        provenance = f"ipeds:{institution.unitid}"

        claims.extend(
            [
                Claim(
                    tenant_id=IPEDS_TENANT_ID,
                    domain="campus",
                    entity_type="executive_summary",
                    entity_id=entity_id,
                    claim_key="kpi_value",
                    value_number=institution.total_fte,
                    provenance=provenance,
                    sensitivity=ClaimSensitivity.internal,
                    compliance_tags=["IPEDS"],
                ),
                Claim(
                    tenant_id=IPEDS_TENANT_ID,
                    domain="campus",
                    entity_type="executive_summary",
                    entity_id=entity_id,
                    claim_key="trend_delta",
                    value_number=institution.graduate_mix_delta,
                    provenance=provenance,
                    sensitivity=ClaimSensitivity.internal,
                    compliance_tags=["IPEDS"],
                ),
                Claim(
                    tenant_id=IPEDS_TENANT_ID,
                    domain="campus",
                    entity_type="institution_enrollment_summary",
                    entity_id=entity_id,
                    claim_key="total_enrollment",
                    value_number=institution.total_enrollment,
                    provenance=provenance,
                    sensitivity=ClaimSensitivity.internal,
                    compliance_tags=["IPEDS"],
                ),
                Claim(
                    tenant_id=IPEDS_TENANT_ID,
                    domain="campus",
                    entity_type="institution_enrollment_summary",
                    entity_id=entity_id,
                    claim_key="institution_count",
                    value_number=1,
                    provenance=provenance,
                    sensitivity=ClaimSensitivity.internal,
                    compliance_tags=["IPEDS"],
                ),
                Claim(
                    tenant_id=IPEDS_TENANT_ID,
                    domain="admissions",
                    entity_type="admin_function_summary",
                    entity_id=entity_id,
                    admin_function="admissions",
                    claim_key="function_metric",
                    value_number=100 if institution.open_admissions_flag else 0,
                    provenance=provenance,
                    sensitivity=ClaimSensitivity.internal,
                    compliance_tags=["IPEDS"],
                ),
                Claim(
                    tenant_id=IPEDS_TENANT_ID,
                    domain="admissions",
                    entity_type="admin_function_summary",
                    entity_id=entity_id,
                    admin_function="admissions",
                    claim_key="record_count",
                    value_number=1,
                    provenance=provenance,
                    sensitivity=ClaimSensitivity.internal,
                    compliance_tags=["IPEDS"],
                ),
                Claim(
                    tenant_id=IPEDS_TENANT_ID,
                    domain="admin",
                    entity_type="institution_catalog",
                    entity_id=entity_id,
                    claim_key="profile",
                    value_json={
                        "unitid": institution.unitid,
                        "name": institution.name,
                        "city": institution.city,
                        "state": institution.state,
                        "website": institution.website,
                    },
                    provenance=provenance,
                    sensitivity=ClaimSensitivity.low,
                    compliance_tags=["IPEDS"],
                ),
            ]
        )

    return claims


def seed_ipeds_claims(db: Session) -> int:
    if not _csv_exists():
        print("IPEDS seed skipped: one or more CSV files are missing")
        return 0

    institutions = _build_institutions()
    if not institutions:
        print("IPEDS seed skipped: no matching institution rows were found")
        return 0

    _seed_tenant(db)
    db.flush()
    db.add_all(_build_claims(institutions))
    print(f"Seeded IPEDS CSV claims with {len(institutions)} institutions")
    return len(institutions)
