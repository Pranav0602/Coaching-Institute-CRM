from django.apps import AppConfig  # type: ignore[import]


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self) -> None:
        # `institute_crm` is the project package, not an installed app, so its system
        # checks need an explicit import to register. `accounts` is the foundational app
        # (it owns AUTH_USER_MODEL), which makes it the natural host for this hook.
        # When the `rag` app lands it will register its own checks in RagConfig.ready().
        from institute_crm import checks  # noqa: F401  (import registers the checks)
