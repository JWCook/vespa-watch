# Generated by Django 2.1.8 on 2019-07-25 08:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vespawatch', '0024_auto_20190724_1543'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='taxon',
            name='identification_picture_individual',
        ),
        migrations.RemoveField(
            model_name='taxon',
            name='identification_picture_nest',
        ),
        migrations.RemoveField(
            model_name='taxon',
            name='identification_priority',
        ),
    ]
