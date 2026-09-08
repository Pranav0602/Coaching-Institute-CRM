"""
Audit Log Middleware to capture API actions automatically.
"""
from accounts.models import AuditLog

class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Log mutating requests (POST, PUT, PATCH, DELETE) by authenticated users
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and request.user.is_authenticated:
            try:
                ip = request.META.get('REMOTE_ADDR')
                AuditLog.objects.create(
                    actor=request.user,
                    action=f"HTTP_{request.method}",
                    model_name="API_REQUEST",
                    target_id=request.path[:128],
                    changes={"path": request.path, "status_code": response.status_code},
                    ip_address=ip
                )
            except Exception:
                pass

        return response
