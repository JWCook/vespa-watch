# Generated by Django 2.2.24 on 2021-08-23 14:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vespawatch', '0048_populate_product_existing_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='managementaction',
            name='method',
            field=models.CharField(blank=True, choices=[('FR', 'Freezer'), ('TH', 'Telescopic handle'), ('KJ', 'Killing jar/box'), ('LS', 'Liquid sprayer'), ('PD', 'Powder distributor'), ('NNT', 'Nest not treated'), ('O', 'Other'), ('UK', 'Unknown')], max_length=3, verbose_name='Method'),
        ),
    ]