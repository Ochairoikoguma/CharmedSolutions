import logging
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from accounting.services.csv_import import (
    MAX_UPLOAD, active_reporting_period, parse_simplicity_export, persist_simplicity_export,
)

logger = logging.getLogger(__name__)


@require_GET
def reporting_period(request):
    period = active_reporting_period()
    return JsonResponse({"year": period.year if period else None, "month": period.month if period else None})


@require_POST
def import_csv(request):
    if connection.vendor != "mysql":
        return JsonResponse({"error": "Connect the app to MySQL before importing."}, status=400)
    uploaded = request.FILES.get("file")
    if uploaded is None or not uploaded.name.lower().endswith(".csv"):
        return JsonResponse({"error": "Choose a CSV file."}, status=400)
    if uploaded.size > MAX_UPLOAD:
        return JsonResponse({"error": "CSV must be 5 MB or smaller."}, status=400)
    try:
        parsed = parse_simplicity_export(uploaded.read())
        result = persist_simplicity_export(parsed, uploaded.name)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except DatabaseError:
        logger.exception("CSV import rolled back")
        return JsonResponse({"error": "Database import failed. No rows from this upload were saved; check the server terminal."}, status=500)
    return JsonResponse(result, status=201)
