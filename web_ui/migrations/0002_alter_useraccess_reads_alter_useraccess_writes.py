# Generated by Django 4.2.17 on 2025-01-01 11:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web_ui', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='useraccess',
            name='reads',
            field=models.BooleanField(),
        ),
        migrations.AlterField(
            model_name='useraccess',
            name='writes',
            field=models.BooleanField(),
        ),
    ]
