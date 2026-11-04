from django.db import connection
from django.http import JsonResponse


def health(request):
    """Public liveness/readiness probe used by the frontend shell and Docker."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()[0].split(" on ")[0]
        return JsonResponse({"status": "ok", "database": db_version})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"status": "error", "detail": str(exc)}, status=503)
