# Generated by Django 4.0.2 on 2022-05-21 14:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gutschrift',
            name='grund',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Rechnungsposition'),
        ),
        migrations.AlterField(
            model_name='gutschrift',
            name='rechnungsposition',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Rechnungsposition'),
        ),
        migrations.AlterField(
            model_name='invoicerechnungspositionen',
            name='rechnungsbereich',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Rechnungsbereich'),
        ),
        migrations.AlterField(
            model_name='invoicerechnungspositionen',
            name='rechnungsposition',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Rechnungsposition'),
        ),
    ]