"""
Global base model, soft-delete plumbing and shared query helpers.

Every domain model inherits :class:`BaseModel`, which gives it a UUID primary key,
created/updated stamps, optimistic-locking ``version`` counter and soft deletion. Rows are
never removed by the application: :meth:`BaseModel.soft_delete` flips ``is_deleted`` so
history, audit trails and financial records stay intact and referentially valid.

Because ``is_deleted`` is opt-out rather than opt-in, every read path must filter it. Use
:func:`active` or :class:`SoftDeleteManager` rather than hand-writing the filter, so a
missed ``is_deleted=False`` cannot silently leak deleted rows into an API response.
"""
import uuid

from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    """Default manager that hides soft-deleted rows.

    Attach as ``objects`` only where *no* code needs the deleted rows; otherwise keep the
    plain manager and go through :func:`active` at the call site, so an admin or repair
    script can still reach them.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True

    def soft_delete(self, *, using=None) -> None:
        """Hide the row without deleting it. Idempotent."""
        if self.is_deleted:
            return
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"], using=using)

    def restore(self, *, using=None) -> None:
        """Undo a soft delete. Used by admin correction flows."""
        if not self.is_deleted:
            return
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"], using=using)

    def save(self, *args, **kwargs):
        if self.pk and not kwargs.get("force_insert", False):
            self.version += 1
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                # A partial save must still persist the fields we just mutated, otherwise
                # the version counter and the modification stamp silently drift from
                # reality - which would make the optimistic-locking counter useless.
                kwargs["update_fields"] = set(update_fields) | {"version", "updated_at"}
        super().save(*args, **kwargs)


def active(model_or_queryset):
    """Return the non-deleted rows of a model class or queryset.

    ``active(Batch)`` and ``active(some_batch_qs)`` both work, which keeps service code
    free of repeated ``filter(is_deleted=False)`` and makes the omission of a filter
    visible in review.
    """
    queryset = (
        model_or_queryset._default_manager.all()
        if isinstance(model_or_queryset, type) and issubclass(model_or_queryset, models.Model)
        else model_or_queryset
    )
    return queryset.filter(is_deleted=False)
