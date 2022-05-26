# Generated by Django 4.0.2 on 2022-02-11 17:13

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import files.models
import files.utils


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='GutschriftFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.FileField(upload_to='', validators=[files.models.validate_gutschrift, django.core.validators.FileExtensionValidator(['xls'])])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Gutschrift',
                'verbose_name_plural': 'Gutschriften',
            },
        ),
        migrations.CreateModel(
            name='InvoiceFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.FileField(upload_to='', validators=[files.models.validate_invoice, django.core.validators.FileExtensionValidator(['xls'])])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Rechnung',
                'verbose_name_plural': 'Rechnungen',
            },
        ),
        migrations.CreateModel(
            name='InvoiceGrunddaten',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rechnungsnummer', models.TextField(verbose_name='Rechnungsnummer')),
                ('rahmenvertragsnummer', models.TextField(verbose_name='Rahmenvertragsnummer')),
                ('umsatzsteuer', models.DecimalField(decimal_places=2, max_digits=4)),
                ('abrechnungsperiode_start', models.DateTimeField(verbose_name='Abrechnungsperiode (Start)')),
                ('abrechnungsperiode_ende', models.DateTimeField(verbose_name='Abrechnungsperiode (Ende)')),
                ('rechnungsmonat_komplett', models.BooleanField(verbose_name='Abrechnungsmonat komplett')),
                ('rechnung_betrag_dtag_netto', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Betrag DTAG (netto)')),
                ('rechnung_betrag_dtag_brutto', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Betrag DTAG (brutto)')),
                ('rechnung_betrag_drittanbieter_brutto', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Betrag Drittanbieter (brutto)')),
                ('rechnung_betrag_vda_brutto', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Allgemeine Kosten VDA (brutto)')),
                ('rechnung_summe_netto', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Rechnungssumme (netto)')),
                ('rechnung_summe_brutto', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Rechnungssumme (brutto)')),
                ('rechnung_summe_brutto_berechnet', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='berechnete Rechnungssumme (brutto)')),
                ('from_file', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='files.invoicefile')),
            ],
        ),
        migrations.CreateModel(
            name='Kostenstelle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kostenstelle', models.TextField(blank=True, editable=False, null=True, verbose_name='Kostenstelle')),
            ],
            options={
                'verbose_name': 'Kostenstelle',
                'verbose_name_plural': 'Kostenstellen',
                'ordering': ['kostenstelle'],
            },
        ),
        migrations.CreateModel(
            name='MasterReportFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.FileField(upload_to='', validators=[files.utils.validate_or_process_masterreport, django.core.validators.FileExtensionValidator(['xlsx'])])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Masterreport',
                'verbose_name_plural': 'Masterreports',
            },
        ),
        migrations.CreateModel(
            name='MasterReportData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rahmenvertrag', models.TextField(editable=False, verbose_name='Rahmenvertrag')),
                ('rufnummer', models.TextField(editable=False, verbose_name='Rufnummer')),
                ('kostenstellennutzer', models.TextField(blank=True, null=True, verbose_name='Kostenstellennutzer')),
                ('datenoptionen', models.TextField(blank=True, null=True, verbose_name='Daten Optionen')),
                ('voiceoptionen', models.TextField(blank=True, null=True, verbose_name='Voice Optionen')),
                ('roamingoptionen', models.TextField(blank=True, null=True, verbose_name='Roaming Optionen')),
                ('sonstigeoptionen', models.TextField(blank=True, null=True, verbose_name='Sonstige Optionen')),
                ('evn', models.TextField(blank=True, null=True, verbose_name='EVN')),
                ('vertragsbeginn', models.DateTimeField(blank=True, null=True, verbose_name='Vertragsbeginn')),
                ('bindefristende', models.DateTimeField(blank=True, null=True, verbose_name='Bindefristende')),
                ('tarif', models.TextField(blank=True, null=True, verbose_name='Tarif')),
                ('vvlberechtigung', models.BooleanField(verbose_name='VVL Berechtigung')),
                ('kuendigungstermin', models.DateTimeField(blank=True, null=True, verbose_name='Kündigungstermin')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('exported_at', models.DateTimeField(verbose_name='Datenstand')),
                ('from_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='files.masterreportfile')),
                ('kostenstelle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='files.kostenstelle')),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceRechnungsPositionen',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kartennummer', models.CharField(blank=True, max_length=25, null=True, verbose_name='Kartennummer')),
                ('kostenstellennutzer', models.CharField(blank=True, max_length=80, null=True, verbose_name='Kostenstellennutzer')),
                ('rufnummer', models.CharField(blank=True, max_length=25, null=True, verbose_name='Rufnummer')),
                ('rechnungsbereich', models.CharField(blank=True, max_length=50, null=True, verbose_name='Rechnungsbereich')),
                ('rechnungsposition', models.CharField(blank=True, max_length=50, null=True, verbose_name='Rechnungsposition')),
                ('menge', models.IntegerField(blank=True, null=True, verbose_name='Menge')),
                ('infomenge', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Infomenge')),
                ('einheit', models.CharField(blank=True, max_length=50, null=True, verbose_name='Einheit')),
                ('beginn_datum', models.DateTimeField(blank=True, null=True, verbose_name='Beginn-Datum')),
                ('ende_datum', models.DateTimeField(blank=True, null=True, verbose_name='Ende-Datum')),
                ('info_betrag', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='Info-Betrag')),
                ('eur_netto', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='EUR (Netto)')),
                ('summe_nettobetrag', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='Summen Nettobetrag')),
                ('andere_leistungen_eur_brutto', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='Andere Leistungen EUR (brutto)')),
                ('summen_brutto_betraege', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='Summen Brutto-beträge')),
                ('grunddaten', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='files.invoicegrunddaten')),
                ('kostenstelle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='files.kostenstelle')),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kartennummer', models.CharField(max_length=25, verbose_name='Kartennummer')),
                ('rufnummer', models.CharField(max_length=25, verbose_name='Rufnummer')),
                ('kostenstellennutzer', models.CharField(blank=True, max_length=80, null=True, verbose_name='Kostenstellennutzer')),
                ('betrag_dtag_brutto', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Betrag DTAG (brutto)')),
                ('fixkosten', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Fixkosten (brutto)')),
                ('variable_kosten', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='variable Kosten (brutto)')),
                ('drittanbieterkosten', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Drittanbieterkosten (brutto)')),
                ('summe_komplett_brutto', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Rechnungssumme (brutto)')),
                ('grunddaten', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='files.invoicegrunddaten')),
                ('kostenstelle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='files.kostenstelle')),
            ],
        ),
        migrations.CreateModel(
            name='Gutschrift',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gutschriftsnummer', models.TextField(verbose_name='Gutschriftsnummer')),
                ('rechnungsnummer', models.TextField(verbose_name='Rechnungsnummer')),
                ('kartennummer', models.CharField(blank=True, max_length=25, null=True, verbose_name='Kartennummer')),
                ('kostenstellennutzer', models.CharField(blank=True, max_length=80, null=True, verbose_name='Kostenstellennutzer')),
                ('rufnummer', models.CharField(blank=True, max_length=25, null=True, verbose_name='Rufnummer')),
                ('rechnungsposition', models.CharField(blank=True, max_length=50, null=True, verbose_name='Rechnungsposition')),
                ('eur_netto', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='EUR (Netto)')),
                ('eur_brutto', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='EUR (Netto)')),
                ('grund', models.CharField(blank=True, max_length=50, null=True, verbose_name='Rechnungsposition')),
                ('from_file', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='files.gutschriftfile')),
                ('kostenstelle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='files.kostenstelle')),
            ],
        ),
    ]