# Generated by Django 2.2.24 on 2021-08-19 11:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vespawatch', '0043_managementaction_nest_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='managementaction',
            name='aftercare',
            field=models.CharField(blank=True, choices=[('NCR', 'Nest completely removed'), ('NPR', 'Nest partially removed'), ('NNR', 'Nest not removed'), ('UK', 'Unknown')], max_length=3, verbose_name='Aftercare'),
        ),
    ]