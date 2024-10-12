from django.db import models

class UserAccess(models.Model):
    username = models.CharField(max_length=200)
    path = models.CharField(max_length=255)
    reads = models.JSONField()
    writes = models.JSONField()

class DownloadToken(models.Model):
    username = models.CharField(max_length=200)
    path = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    uuid = models.CharField(max_length=32)
