# Generated by Django 3.0.5 on 2020-04-03 14:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0006_auto_20200403_1400'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facilitymetrics',
            name='icu_beds_capacity',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='facilitymetrics',
            name='icu_beds_used',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='facilitymetrics',
            name='med_beds_capacity',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='facilitymetrics',
            name='med_beds_used',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='facilitymetrics',
            name='ventilators_capacity',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='facilitymetrics',
            name='ventilators_used',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]