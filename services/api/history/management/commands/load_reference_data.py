from django.core.management.base import BaseCommand

from history.loader import load_all


class Command(BaseCommand):
    help = "Load the source directory and the checked Cheap Street reference facts."

    def handle(self, *args, **options):
        counts = load_all()
        summary = ", ".join(f"{n} {name}" for name, n in counts.items())
        self.stdout.write(self.style.SUCCESS(f"Loaded {summary}."))
