# Generated by Django 2.2.1 on 2019-05-27 09:16

import django.core.validators
from django.db import migrations, models
import markdownx.models


class Migration(migrations.Migration):

    dependencies = [
        ('vespawatch', '0019_auto_20190524_0906'),
    ]

    operations = [
        migrations.AddField(
            model_name='identificationcard',
            name='description_fr',
            field=markdownx.models.MarkdownxField(blank=True, null=True, verbose_name='Description'),
        ),
        migrations.AddField(
            model_name='taxon',
            name='vernacular_name_fr',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Vernacular name'),
        ),
        migrations.AlterField(
            model_name='individual',
            name='latitude',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)], verbose_name='Latitude'),
        ),
        migrations.AlterField(
            model_name='individual',
            name='longitude',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)], verbose_name='Longitude'),
        ),
        migrations.AlterField(
            model_name='nest',
            name='latitude',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)], verbose_name='Latitude'),
        ),
        migrations.AlterField(
            model_name='nest',
            name='longitude',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)], verbose_name='Longitude'),
        ),
    ]