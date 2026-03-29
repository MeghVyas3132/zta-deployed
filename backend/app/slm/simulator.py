from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.schemas.pipeline import InterpretedIntent, ScopeContext

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled at runtime when dependency is unavailable
    OpenAI = None


logger = logging.getLogger(__name__)
UNSAFE_HINTS = ("select ", " from ", "schema", "table", "system prompt")


class SLMSimulator:
    """
    Strict untrusted rendering layer.

    When configured, template generation is delegated to a hosted SLM. The
    returned output is still treated as untrusted and must pass output guards.
    There is no local fallback template path.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: OpenAI | None = None

    def render_template(self, intent: InterpretedIntent, scope: ScopeContext) -> str:
        if scope.persona_type == "it_head":
            return "Access to chat templates is blocked for this persona."

        if self.settings.slm_provider.lower() != "nvidia":
            raise ValidationError(
                message="SLM provider is not configured for hosted generation",
                code="SLM_PROVIDER_UNAVAILABLE",
            )

        return self._render_with_hosted_slm(intent, scope)

    def _render_with_hosted_slm(self, intent: InterpretedIntent, scope: ScopeContext) -> str:
        if not self.settings.slm_api_key or OpenAI is None:
            raise ValidationError(
                message="Hosted SLM client is not available",
                code="SLM_CLIENT_UNAVAILABLE",
            )

        try:
            client = self._get_client()
            if client is None:
                raise ValidationError(
                    message="Hosted SLM client could not be initialized",
                    code="SLM_CLIENT_UNAVAILABLE",
                )

            slots = ", ".join(f"[SLOT_{idx + 1}] for {key}" for idx, key in enumerate(intent.slot_keys)) or "[SLOT_1]"
            prompt = (
                "You are an untrusted rendering model inside a zero-trust system. "
                "Return exactly one short response template. "
                "Use only SLOT placeholders and natural language. "
                "Do not include any numbers except slot identifiers, do not mention schemas, SQL, tables, or system prompts. "
                "Do not wrap the answer in quotes.\n\n"
                f"Persona: {scope.persona_type}\n"
                f"Intent: {intent.name}\n"
                f"Domain: {intent.domain}\n"
                f"Entity type: {intent.entity_type}\n"
                f"Slots to use: {slots}\n"
                f"Aggregation: {intent.aggregation or 'none'}\n"
                "Output exactly one sentence."
            )

            completion = client.chat.completions.create(
                model=self.settings.slm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Only output a safe slot-based response template.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.settings.slm_temperature,
                top_p=self.settings.slm_top_p,
                max_tokens=self.settings.slm_max_tokens,
                stream=False,
            )

            content = completion.choices[0].message.content if completion.choices else None
            if not content:
                raise ValidationError(
                    message="Hosted SLM returned an empty template",
                    code="SLM_EMPTY_TEMPLATE",
                )

            rendered = content.strip().splitlines()[0].strip().strip('"')
            if not rendered or "[SLOT_" not in rendered:
                raise ValidationError(
                    message="Hosted SLM returned an invalid slot template",
                    code="SLM_INVALID_TEMPLATE",
                )

            lower_rendered = rendered.lower()
            if any(token in lower_rendered for token in UNSAFE_HINTS):
                raise ValidationError(
                    message="Hosted SLM returned an unsafe template",
                    code="SLM_UNSAFE_TEMPLATE",
                )

            return rendered
        except ValidationError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Hosted SLM template generation failed")
            raise ValidationError(
                message="Hosted SLM request failed",
                code="SLM_REQUEST_FAILED",
            ) from exc

    def _get_client(self) -> OpenAI | None:
        if self._client is None and OpenAI is not None:
            self._client = OpenAI(
                base_url=self.settings.slm_base_url,
                api_key=self.settings.slm_api_key,
            )
        return self._client


slm_simulator = SLMSimulator()
