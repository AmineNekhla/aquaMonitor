"""

Manually trigger AI inference for all ponds or a specific pond.

Usage:
    python manage.py run_ai_inference
    python manage.py run_ai_inference --pond-id 1
    python manage.py run_ai_inference --no-forecast
"""

from django.core.management.base import BaseCommand
from monitoring.models import Pond
from monitoring.ai_inference import run_inference_for_pond, run_inference_all_ponds


class Command(BaseCommand):
    help = "Run Aqua AI inference — classifies water quality and saves alerts to DB"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pond-id", type=int, default=None,
            help="Run inference for a specific pond ID only"
        )
        parser.add_argument(
            "--no-forecast", action="store_true",
            help="Skip Model 2 forecast (faster, only runs Model 1)"
        )

    def handle(self, *args, **options):
        pond_id     = options["pond_id"]
        no_forecast = options["no_forecast"]
        save_forecast = not no_forecast

        self.stdout.write("=" * 50)
        self.stdout.write("Aqua AI Inference")
        self.stdout.write("=" * 50)

        if pond_id:
            try:
                pond = Pond.objects.get(id=pond_id)
                self.stdout.write(f"Running inference for pond: {pond}")
                result = run_inference_for_pond(pond, save_forecast=save_forecast)
                self._print_result(result)
            except Pond.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Pond with ID {pond_id} not found."))
        else:
            self.stdout.write("Running inference for all active ponds...")
            results = run_inference_all_ponds(save_forecast=save_forecast)
            for result in results:
                self._print_result(result)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Inference complete."))

    def _print_result(self, result: dict):
        status = result.get("status", "unknown")
        error  = result.get("error")
        pond   = result.get("pond", "?")

        if error:
            self.stdout.write(self.style.ERROR(f"  [{pond}] ERROR: {error}"))
            return

        color = {
            "Good":    self.style.SUCCESS,
            "Warning": self.style.WARNING,
            "Risk":    self.style.ERROR,
        }.get(status, self.style.NOTICE)

        self.stdout.write(color(f"  [{pond}] Status: {status}"))

        if result.get("alert_saved"):
            self.stdout.write(self.style.WARNING(f"    → Alert saved to DB"))

        forecast = result.get("forecast")
        if forecast:
            risk_hours = [f"+{h['hour']}h" for h in forecast if h["status"] == "Risk"]
            if risk_hours:
                self.stdout.write(self.style.ERROR(
                    f"    → Risk predicted at: {', '.join(risk_hours)}"
                ))
            else:
                self.stdout.write(self.style.SUCCESS("    → No risk predicted in next 6h"))