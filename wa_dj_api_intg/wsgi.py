"""
WSGI config for wa_dj_api_intg project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os,sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wa_dj_api_intg.settings')

application = get_wsgi_application()
