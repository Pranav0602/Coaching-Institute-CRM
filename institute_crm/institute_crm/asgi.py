"""
ASGI config for institute_crm project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from institute_crm import token_revocation

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "institute_crm.settings")

application = get_asgi_application()

# See wsgi.py: creates the token_blacklist tables if a deploy reached production without
# them, so a worker never starts in a state where every sign-in would 500.
token_revocation.repair_missing_tables()
