from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wa_dj_api_intg.settings')
app = Celery('wa_dj_api_intg')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

#/work/progs/wa_dj_api_intg/wa_dj_api_intg/wa_dj_api_intg