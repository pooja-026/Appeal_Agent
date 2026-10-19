"""One explicit, bounded live-analysis smoke test for a local configured environment."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from appeal_agent.config import get_settings
from appeal_agent.models import Case, Document, DocumentType, Passage
from appeal_agent.providers import AnalysisProviderError, AnthropicAnalysisProvider


def build_case() -> Case:
    return Case(
        case_id="smoke-fictional-case",
        title="Fictional damaged mug refund denial",
        created_at=datetime.now(timezone.utc),
        documents=[
            Document(
                document_id="smoke-denial",
                document_type=DocumentType.DENIAL,
                title="Fictional denial",
                passages=[Passage(passage_id="smoke-denial-p1", page_number=None, text="Fictional retailer Cedar & Finch denied the refund because the item was marked sale-priced.")],
            ),
            Document(
                document_id="smoke-policy",
                document_type=DocumentType.POLICY,
                title="Fictional policy",
                passages=[Passage(passage_id="smoke-policy-p1", page_number=None, text="Cedar & Finch accepts reports of damaged items within 14 days of delivery, including sale-priced items.")],
            ),
        ],
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Make one bounded Anthropic Appeal Agent smoke call.")
    parser.add_argument("--live", action="store_true", help="Required: explicitly permit one live generation request.")
    args = parser.parse_args()
    if not args.live:
        parser.error("refusing to run without --live; this flag is required for the one paid generation call")

    settings = get_settings()
    if settings.ai_provider != "anthropic":
        raise SystemExit("Set AI_PROVIDER=anthropic in the backend environment before running this script.")

    try:
        provider = AnthropicAnalysisProvider(settings)
        analysis = await provider.analyze(build_case())
    except AnalysisProviderError as exc:
        print(json.dumps({"error": str(exc), "code": exc.code}, indent=2))
        raise SystemExit(1) from exc

    print(json.dumps({"analysis": analysis.model_dump(mode="json"), "usage": provider.last_usage.__dict__ if provider.last_usage else None}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
