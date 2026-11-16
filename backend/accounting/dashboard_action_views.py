import json
import logging

from django.db import DatabaseError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from accounting.services.csv_import import active_reporting_period
from accounting.services.dashboard_actions import period_bounds, reports_for_clients, rollover_clients

logger = logging.getLogger(__name__)


def read_request(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("Invalid JSON request.") from error
    if not isinstance(data, dict):
        raise ValueError("Invalid request.")
    start, _ = period_bounds(data.get("year"), data.get("month"))
    if start != active_reporting_period():
        raise ValueError("The imported reporting month changed. Refresh the dashboard.")
    return data


def selected_ids(data, limit):
    ids = data.get("client_ids")
    if not isinstance(ids, list) or not 1 <= len(ids) <= limit:
        raise ValueError(f"Select between 1 and {limit} clients.")
    if any(type(value) is not int or value < 1 for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Client IDs must be distinct positive integers.")
    return ids


@require_POST
def rollover_dashboard(request):
    try:
        data = read_request(request)
        mode = data.get("mode")
        if mode not in ("selected", "all"):
            raise ValueError("Choose selected or all clients.")
        ids = selected_ids(data, 10) if mode == "selected" else None
        result = rollover_clients(data["year"], data["month"], ids)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except DatabaseError:
        logger.exception("Dashboard rollover failed")
        return JsonResponse({"error": "Rollover failed; all changes were rolled back."}, status=500)
    return JsonResponse(result)


@require_POST
def download_page_reports(request):
    try:
        data = read_request(request)
        ids = selected_ids(data, 10)
        pdf_zip = reports_for_clients(data["year"], data["month"], ids)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except DatabaseError:
        logger.exception("Bulk report generation failed")
        return JsonResponse({"error": "Report generation failed; all new reports and cost changes were rolled back."}, status=500)
    response = HttpResponse(pdf_zip, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="remittance_reports_{data["year"]:04d}_{data["month"]:02d}.zip"'
    )
    return response
