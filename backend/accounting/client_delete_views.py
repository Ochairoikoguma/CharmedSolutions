"""Confirmed client deletion, including related accounting records."""
import json
import logging

from django.core import signing
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounting.models import Client, CollectionAccount, Payment, Cost, Remittance
from accounting.import_models import ImportRow

logger = logging.getLogger(__name__)
SALT = "accounting.client-delete.v1"


def related_counts(client_id):
    return {
        "accounts": CollectionAccount.objects.filter(client_id=client_id).count(),
        "payments": Payment.objects.filter(account__client_id=client_id).count(),
        "costs": Cost.objects.filter(account__client_id=client_id).count(),
        "reports": Remittance.objects.filter(client_id=client_id).count(),
    }


@require_GET
def client_delete_preview(request, client_id):
    client = Client.objects.filter(pk=client_id).first()
    if client is None:
        return JsonResponse({"error": "Client not found."}, status=404)
    state = {"id": client.pk, "name": client.client_name, "counts": related_counts(client.pk)}
    return JsonResponse({**state, "confirmation": signing.dumps(state, salt=SALT)})


@require_POST
def delete_client(request, client_id):
    try:
        body = json.loads(request.body)
        if not isinstance(body, dict) or not isinstance(body.get("confirmation"), str):
            raise ValueError()
        expected = signing.loads(body["confirmation"], salt=SALT, max_age=300)
        if expected.get("id") != client_id:
            raise ValueError()
    except (ValueError, UnicodeDecodeError, signing.BadSignature):
        return JsonResponse({"error": "Deletion confirmation is missing, invalid, or expired. Click Delete Client again."}, status=400)

    try:
        with transaction.atomic():
            # Imports, report generation, and rollover also lock this client.
            client = Client.objects.select_for_update().filter(pk=client_id).first()
            if client is None:
                return JsonResponse({"error": "Client not found."}, status=404)
            counts = related_counts(client_id)
            if client.client_name != expected["name"] or counts != expected["counts"]:
                return JsonResponse({"error": "This client's records changed after the confirmation opened. Click Delete Client again to review the updated counts."}, status=409)

            payment_ids = list(Payment.objects.filter(account__client_id=client_id).values_list("pk", flat=True))
            cost_ids = list(Cost.objects.filter(account__client_id=client_id).values_list("pk", flat=True))
            audit_rows = list(ImportRow.objects.select_for_update().filter(
                Q(payment_id__in=payment_ids) | Q(cost_id__in=cost_ids)
            ))
            # Preserve source rows and original IDs as history, and explicitly
            # record why their corresponding live transactions no longer exist.
            deleted_at = timezone.now().isoformat()
            for row in audit_rows:
                row.source = {**row.source, "_deletion": {
                    "client_id": client_id, "client_name": client.client_name,
                    "deleted_at": deleted_at,
                }}
            if audit_rows:
                ImportRow.objects.bulk_update(audit_rows, ["source"])

            # Delete children explicitly: existing models use DO_NOTHING and
            # installations may differ in their MySQL cascade definitions.
            Remittance.objects.filter(client_id=client_id).delete()
            Payment.objects.filter(account__client_id=client_id).delete()
            Cost.objects.filter(account__client_id=client_id).delete()
            CollectionAccount.objects.filter(client_id=client_id).delete()
            client.delete()
    except DatabaseError:
        logger.exception("Client deletion failed and was rolled back")
        return JsonResponse({"error": "Deletion failed. No records were deleted; check the server terminal."}, status=500)

    return JsonResponse({"deleted": client_id, "counts": counts})
