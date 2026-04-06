from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.db.models import DomainKeyword, IntentDefinition
from app.interpreter.domain_gate import AGGREGATION_MODIFIERS
from app.interpreter.intent_extractor import IntentRule


def _normalize_keywords(values: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if not values:
        return ()

    normalized: list[str] = []
    for value in values:
        keyword = str(value).strip().lower()
        if keyword and keyword not in normalized:
            normalized.append(keyword)
    return tuple(normalized)


def load_domain_keywords(
    db: Session,
    tenant_id: str,
) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    rows = db.scalars(
        select(DomainKeyword).where(
            DomainKeyword.tenant_id == tenant_id,
            DomainKeyword.is_active.is_(True),
        )
    ).all()

    loaded: dict[str, tuple[str, ...]] = {}
    for row in rows:
        keywords = _normalize_keywords(row.keywords)
        if not keywords:
            continue
        loaded[row.domain] = keywords

    if not loaded:
        raise ValidationError(
            message="No active domain keyword configuration is available for this tenant",
            code="DOMAIN_KEYWORDS_NOT_CONFIGURED",
        )

    return loaded, AGGREGATION_MODIFIERS


def load_intent_rules(db: Session, tenant_id: str) -> tuple[IntentRule, ...]:
    rows = db.scalars(
        select(IntentDefinition)
        .where(
            IntentDefinition.tenant_id == tenant_id,
            IntentDefinition.is_active.is_(True),
        )
        .order_by(IntentDefinition.priority.asc(), IntentDefinition.intent_name.asc())
    ).all()

    loaded_rules: list[IntentRule] = []
    for row in rows:
        intent_name = row.intent_name.strip().lower()
        if not intent_name:
            continue

        slot_keys = _normalize_keywords(row.slot_keys)
        keywords = _normalize_keywords(row.keywords)
        persona_types = _normalize_keywords(row.persona_types)

        # slot_keys are required for safe detokenization.
        if not slot_keys:
            continue

        loaded_rules.append(
            IntentRule(
                name=intent_name,
                domain=row.domain,
                entity_type=row.entity_type,
                slot_keys=slot_keys,
                keywords=keywords,
                requires_aggregation=row.requires_aggregation,
                persona_types=persona_types,
                is_default=row.is_default,
                priority=row.priority,
            )
        )

    if not loaded_rules:
        raise ValidationError(
            message="No active intent definition configuration is available for this tenant",
            code="INTENT_RULES_NOT_CONFIGURED",
        )

    return tuple(loaded_rules)
