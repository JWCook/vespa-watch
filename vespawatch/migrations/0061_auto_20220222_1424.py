# Generated by Django 2.2.24 on 2022-02-22 13:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vespawatch', '0060_auto_20220215_1539'),
    ]

    operations = [
        migrations.AlterField(
            model_name='managementaction',
            name='number_of_persons',
            field=models.IntegerField(blank=True, null=True, verbose_name='Number of persons'),
        ),
        migrations.AlterField(
            model_name='managementaction',
            name='product',
            field=models.CharField(blank=True, choices=[('PD', 'Permas-D'), ('LN', 'Liquid nitrogen'), ('V', 'Vespa'), ('FD', 'Ficam D'), ('TP', 'Topscore PAL'), ('EE', 'Ether / acetone / ethyl acetate'), ('DE', 'Diatomaceous earth'), ('O', 'Other'), ('N', 'None'), ('UK', 'Unknown')], default='UK', max_length=3, null=True, verbose_name='Product'),
        ),
    ]
