"""
Service layer for the ``accounts`` app.

Business logic lives here, not in views. Views authenticate, validate input with a
serializer, call exactly one service method, and serialise the result.

Conventions every service module in this project follows:

* One ``XxxService`` class per module, containing only ``@staticmethod``s. No state.
* ``@transaction.atomic`` stacked below ``@staticmethod`` on any multi-write operation.
* Failures raise ``institute_crm.exceptions.DomainError`` subclasses - never DRF
  exceptions (that would couple the domain to HTTP) and never bare ``ValueError``
  (indistinguishable from a bug).
* The acting user is passed explicitly (``actor=``). Services never touch ``request``.
* Audit entries are written with ``institute_crm.audit.record_audit`` inside the same
  transaction as the change.
"""
from accounts.services.auth_service import AuthService
from accounts.services.branch_service import BranchService
from accounts.services.user_service import UserService

__all__ = ["AuthService", "BranchService", "UserService"]
