"""Run the evaluation questions against the real assistant and grade the answers.

Costs API credit, so it only runs with --live. Example:
    python manage.py run_evals --live
    python manage.py run_evals --live --only pigeons-address --report evals.json
"""

import asyncio
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from assistant.evals.checks import grade
from assistant.providers import USER_MESSAGES, AnthropicProvider, FinalReply, ProviderError
from assistant.tools import ToolKit
from history.loader import load_all
from history.models import SourceRecord

QUESTIONS = Path(__file__).resolve().parents[2] / "evals" / "questions.json"


class Command(BaseCommand):
    help = "Ask the evaluation questions and grade the answers (uses API credit)."

    def add_arguments(self, parser):
        parser.add_argument("--live", action="store_true", help="Confirm spending API credit.")
        parser.add_argument("--only", help="Run one question by id.")
        parser.add_argument("--report", help="Write a JSON report to this path.")

    def handle(self, *args, **options):
        if not options["live"]:
            raise CommandError("This calls the real assistant and costs credit. Add --live.")
        load_all()
        user, _ = User.objects.get_or_create(
            email="evals@archivehub.invalid", defaults={"display_name": "Evaluations"}
        )
        cases = json.loads(QUESTIONS.read_text(encoding="utf-8"))
        if options["only"]:
            cases = [c for c in cases if c["id"] == options["only"]]
            if not cases:
                raise CommandError(f"No question with id {options['only']!r}.")

        report, failures = [], 0
        for case in cases:
            try:
                answer, kit = asyncio.run(self.ask(case["question"], user))
            except ProviderError as exc:
                raise CommandError(USER_MESSAGES.get(exc.kind, str(exc))) from exc
            sources = kit.cited_in(answer)
            record_keys = set(
                SourceRecord.objects.filter(
                    id__in=[s["id"] for s in sources if s["kind"] == "record"]
                ).values_list("key", flat=True)
            )
            checks = grade(
                case,
                answer,
                valid_numbers={c.n for c in kit.citations.values()},
                cited_record_keys=record_keys,
                source_urls={c.url for c in kit.citations.values() if c.url},
            )
            passed = all(c.passed for c in checks)
            failures += not passed
            mark = self.style.SUCCESS("PASS") if passed else self.style.ERROR("FAIL")
            self.stdout.write(f"\n{mark} {case['id']}: {case['question']}")
            for c in checks:
                tick = "✓" if c.passed else "✗"
                self.stdout.write(f"   {tick} {c.name}{' — ' + c.detail if c.detail else ''}")
            report.append(
                {
                    "id": case["id"],
                    "passed": passed,
                    "answer": answer,
                    "checked": kit.checked,
                    "sources": sources,
                    "checks": [vars(c) for c in checks],
                }
            )

        self.stdout.write(f"\n{len(cases) - failures}/{len(cases)} passed.")
        if options["report"]:
            Path(options["report"]).write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            self.stdout.write(f"Report written to {options['report']}.")

    async def ask(self, question: str, user) -> tuple[str, ToolKit]:
        kit = ToolKit(user=user)
        provider = AnthropicProvider()
        answer = ""
        async for event in provider.stream_reply([{"role": "user", "content": question}], kit):
            if isinstance(event, FinalReply):
                answer = event.text
        return answer, kit
