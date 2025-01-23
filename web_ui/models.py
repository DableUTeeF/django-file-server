from django.db import models

class UserAccess(models.Model):
    username = models.CharField(max_length=200)
    directory = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    reads = models.BooleanField()
    writes = models.BooleanField()

class DownloadToken(models.Model):
    username = models.CharField(max_length=200)
    path = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    uuid = models.CharField(max_length=32)
