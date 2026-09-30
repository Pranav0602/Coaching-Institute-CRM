"""
WSGI config for institute_crm project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from institute_crm import token_revocation

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "institute_crm.settings")

application = get_wsgi_application()

# Migrations belong in the deploy pipeline (build.sh), but a worker that cannot complete
# a sign-in is a total outage with a bare PostgreSQL traceback as the only evidence - so a
# worker that finds the token_blacklist tables missing creates them before it serves
# anything. No-op whenever they are already there. See institute_crm/token_revocation.py.
token_revocation.repair_missing_tables()
