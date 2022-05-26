import os
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import F

from .utils import validate_or_process_gutschrift, validate_or_process_invoice, validate_or_process_masterreport

class customQuerySet(models.QuerySet):
    def managed_by_user(self, user):
        if user.is_superuser:
            return self.all()
        else:
            user_ks = user.feuser.kostenstellen.all()
            return self.filter(kostenstelle__in=user_ks)
    
    def timerange(self, start, end):
        if self.model.__name__ == 'InvoiceGrunddaten':
            return self.filter(
                abrechnungsperiode_start__gte=start,
                abrechnungsperiode_ende__lte=end
            )
        else:
            return self.filter(
                grunddaten__abrechnungsperiode_start__gte=start,
                grunddaten__abrechnungsperiode_ende__lte=end
            )

    def in_month(self, year, month):
        if self.model.__name__ == 'InvoiceGrunddaten':
            return self.filter(
                abrechnungsperiode_start__year__gte=year,
                abrechnungsperiode_start__month__gte=month,
                abrechnungsperiode_ende__year__lte=year,
                abrechnungsperiode_ende__month__lte=month,
            )
        else:
            return self.filter(
                grunddaten__abrechnungsperiode_start__year__gte=year,
                grunddaten__abrechnungsperiode_start__month__gte=month,
                grunddaten__abrechnungsperiode_ende__year__lte=year,
                grunddaten__abrechnungsperiode_ende__month__lte=month,
            )

class Kostenstelle(models.Model):
    kostenstelle = models.TextField(verbose_name='Kostenstelle',editable=False, null=True, blank=True)
    def __str__(self):
        if self.kostenstelle is None:
            self.kostenstelle = ''
        return self.kostenstelle
    class Meta:
        ordering = ['kostenstelle']
        verbose_name = 'Kostenstelle'
        verbose_name_plural = 'Kostenstellen'

def validate_invoice(data):
    filename = data.name  
    if InvoiceFile.objects.filter(data=filename).exists():
        raise ValidationError('Die Datei "%s" wurde bereits hochgeladen' % filename)
    try:
        validate_or_process_invoice(data)
    except ValueError as e:
        raise ValidationError('%s' % e)

def validate_masterreport(data):
    filename = data.name  
    if MasterReportFile.objects.filter(data=filename).exists():
        raise ValidationError('Die Datei "%s" wurde bereits hochgeladen' % filename)
    try:
        validate_or_process_masterreport(data)
    except ValueError as e:
        raise ValidationError('%s' % e)

def validate_gutschrift(data):
    filename = data.name
    if GutschriftFile.objects.filter(data=filename).exists():
        raise ValidationError('Die Datei "%s" wurde bereits hochgeladen' % filename)
    try:
        validate_or_process_gutschrift(data)
    except ValueError as e:
        raise ValidationError('%s' % e)

class MasterReportFile(models.Model):
    data = models.FileField(validators=[validate_or_process_masterreport, FileExtensionValidator(['xlsx'])])
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        uploaded_file = self.data.file

        super(MasterReportFile, self).save(*args, **kwargs)
        
        _cleaned_data = validate_or_process_masterreport(uploaded_file)
        
        try:
            row_iter = _cleaned_data.iterrows()
            objs = []
            for _, row in row_iter:
                kostenstelle_id, _ = Kostenstelle.objects.get_or_create(kostenstelle=row['Kostenstelle'])
                objs.append(
                    MasterReportData(
                        rufnummer = row['Rufnummer'],
                        rahmenvertrag = row['Rahmenvertrag'],
                        kostenstelle = kostenstelle_id,
                        kostenstellennutzer = row['Kostenstellennutzer'],
                        datenoptionen = row['Daten Optionen'],
                        voiceoptionen = row['Voice Optionen'],
                        roamingoptionen = row['Roaming Optionen'],
                        sonstigeoptionen = row['Sonstige Optionen'],
                        evn = row['EVN'],
                        vertragsbeginn = row['Vertragsbeginn'],
                        bindefristende = row['Bindefristende'],
                        tarif = row['Tarif'],
                        vvlberechtigung = row['VVL Berechtigung'],
                        kuendigungstermin = row['Kündigungstermin'],
                        exported_at = row['exported_at'],
                        from_file_id = self.id
                    )
                )
            MasterReportData.objects.bulk_create(objs)

        except Exception as e:
            if self.data.file:
                if os.path.isfile(self.data.path):
                        os.remove(self.data.path)
            raise e
    
    class Meta:
        verbose_name = 'Masterreport'
        verbose_name_plural = 'Masterreports'

class MasterReportData(models.Model):
    rahmenvertrag = models.TextField(editable=False, verbose_name='Rahmenvertrag')
    rufnummer = models.TextField(editable=False, verbose_name='Rufnummer')
    kostenstelle = models.ForeignKey(Kostenstelle, on_delete=models.SET_NULL,null=True, blank=True)
    kostenstellennutzer = models.TextField(verbose_name='Kostenstellennutzer',null=True, blank=True)
    datenoptionen = models.TextField(verbose_name='Daten Optionen',null=True, blank=True)
    voiceoptionen = models.TextField(verbose_name='Voice Optionen',null=True, blank=True)
    roamingoptionen = models.TextField(verbose_name='Roaming Optionen',null=True, blank=True)
    sonstigeoptionen = models.TextField(verbose_name='Sonstige Optionen',null=True, blank=True)
    evn = models.TextField(verbose_name='EVN',null=True, blank=True)
    vertragsbeginn = models.DateTimeField(verbose_name='Vertragsbeginn',null=True, blank=True)
    bindefristende = models.DateTimeField(verbose_name='Bindefristende',null=True, blank=True)
    tarif = models.TextField(verbose_name='Tarif',null=True, blank=True)
    vvlberechtigung = models.BooleanField(verbose_name='VVL Berechtigung')
    kuendigungstermin = models.DateTimeField(verbose_name='Kündigungstermin',null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    exported_at = models.DateTimeField(verbose_name='Datenstand')
    from_file =  models.ForeignKey(MasterReportFile, on_delete=models.CASCADE)
    objects = customQuerySet.as_manager()


class InvoiceFile(models.Model):
    data = models.FileField(validators=[validate_invoice, FileExtensionValidator(['xls'])])
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        uploaded_file = self.data.file

        super(InvoiceFile, self).save(*args, **kwargs)
        
        _cleaned_data = validate_or_process_invoice(uploaded_file)
        
        try:
            rechnung_grunddaten = _cleaned_data[0]
            row = rechnung_grunddaten.iloc[0]

            grunddaten = InvoiceGrunddaten.objects.create(
                from_file_id = self.id,
                rechnungsnummer = row['rechnungsnummer'],
                rahmenvertragsnummer = row['rahmenvertragsnummer'],
                umsatzsteuer = row['umsatzsteuer'],
                abrechnungsperiode_start  = row['abrechnungsperiode_start'],
                abrechnungsperiode_ende  = row['abrechnungsperiode_ende'],
                rechnungsmonat_komplett  = row['rechnungsmonat_komplett'],
                rechnung_betrag_dtag_netto  = row['rechnung_betrag_dtag_netto'],
                rechnung_betrag_dtag_brutto  = row['rechnung_betrag_dtag_brutto'],
                rechnung_betrag_drittanbieter_brutto  = row['rechnung_betrag_drittanbieter_brutto'],
                rechnung_betrag_vda_brutto = row['rechnung_betrag_vda_brutto'],
                rechnung_summe_netto  = row['rechnung_summe_netto'],
                rechnung_summe_brutto  = row['rechnung_summe_brutto'],
                rechnung_summe_brutto_berechnet  = row['rechnung_summe_brutto_berechnet'],
            )

            invoice_data = _cleaned_data[1]
            row_iter = invoice_data.iterrows()
            invoice_data.head()
            objs = []
            for _, row in row_iter:
                kostenstelle_id, _ = Kostenstelle.objects.get_or_create(kostenstelle=row['kostenstelle'])
                objs.append(
                    InvoiceData(
                        kartennummer = row['kartennummer'],
                        rufnummer = row['rufnummer'],
                        kostenstelle = kostenstelle_id,
                        kostenstellennutzer = row['kostenstellennutzer'],
                        betrag_dtag_brutto = row['Telekom Deutschland GmbH'],
                        fixkosten = row['grundpreise_echt'],
                        variable_kosten = row['variable_kosten'],
                        drittanbieterkosten = row['drittanbieterkosten'],
                        summe_komplett_brutto = row['summe_komplett_brutto'],
                        grunddaten_id = grunddaten.id
                    )
                )
            
            InvoiceData.objects.bulk_create(objs)

            invoice_rp = _cleaned_data[2]
            row_iter = invoice_rp.iterrows()
            objs = []
            for _, row in row_iter:
                kostenstelle_id, _ = Kostenstelle.objects.get_or_create(kostenstelle=row['kostenstelle'])
                objs.append(
                    InvoiceRechnungsPositionen(
                        kartennummer = row['kartennummer'],
                        kostenstelle = kostenstelle_id,
                        kostenstellennutzer = row['kostenstellennutzer'],
                        rufnummer = row['rufnummer'],
                        rechnungsbereich = row['rechnungsbereich'],
                        rechnungsposition= row['rechnungsposition'],
                        menge = row['menge'],
                        infomenge = row['infomenge'],
                        einheit = row['einheit'],
                        beginn_datum = row['beginn_datum'],
                        ende_datum = row['ende_datum'],
                        info_betrag = row['info_betrag'],
                        eur_netto = row['eur_netto'],
                        summe_nettobetrag = row['summen_nettobetrag'],
                        andere_leistungen_eur_brutto = row['andere_leistungen_eur_brutto'],
                        summen_brutto_betraege = row['summen_brutto_betraege'],
                        grunddaten_id = grunddaten.id
                    )
                )
            InvoiceRechnungsPositionen.objects.bulk_create(objs)

        except Exception as e:
            if self.data.file:
                if os.path.isfile(self.data.path):
                        os.remove(self.data.path)
            raise e
    
    class Meta:
        verbose_name = 'Rechnung'
        verbose_name_plural = 'Rechnungen'

class InvoiceGrunddaten(models.Model):
    from_file =  models.OneToOneField(InvoiceFile, on_delete=models.CASCADE)
    rechnungsnummer = models.TextField(verbose_name='Rechnungsnummer')
    rahmenvertragsnummer = models.TextField(verbose_name='Rahmenvertragsnummer')
    umsatzsteuer = models.DecimalField(max_digits=4, decimal_places=2)
    abrechnungsperiode_start= models.DateTimeField(verbose_name='Abrechnungsperiode (Start)')
    abrechnungsperiode_ende= models.DateTimeField(verbose_name='Abrechnungsperiode (Ende)')
    rechnungsmonat_komplett = models.BooleanField(verbose_name='Abrechnungsmonat komplett')
    rechnung_betrag_dtag_netto = models.DecimalField(verbose_name='Betrag DTAG (netto)', max_digits=7,decimal_places=2)
    rechnung_betrag_dtag_brutto = models.DecimalField(verbose_name='Betrag DTAG (brutto)', max_digits=7, decimal_places=2)
    rechnung_betrag_drittanbieter_brutto = models.DecimalField(verbose_name='Betrag Drittanbieter (brutto)', max_digits=7, decimal_places=2)
    rechnung_betrag_vda_brutto = models.DecimalField(verbose_name='Allgemeine Kosten VDA (brutto)', max_digits=7, decimal_places=2)
    rechnung_summe_netto = models.DecimalField(verbose_name='Rechnungssumme (netto)', max_digits=7, decimal_places=2)
    rechnung_summe_brutto = models.DecimalField(verbose_name='Rechnungssumme (brutto)', max_digits=7, decimal_places=2)
    rechnung_summe_brutto_berechnet = models.DecimalField(verbose_name='berechnete Rechnungssumme (brutto)', max_digits=7, decimal_places=2)
    objects = customQuerySet.as_manager()

class InvoiceData(models.Model):
    kartennummer = models.CharField(max_length=25,verbose_name='Kartennummer')
    rufnummer = models.CharField(max_length=25,verbose_name='Rufnummer')
    kostenstelle = models.ForeignKey(Kostenstelle, on_delete=models.SET_NULL, null=True, blank=True)
    kostenstellennutzer = models.CharField(max_length=80,verbose_name='Kostenstellennutzer', null=True, blank=True)
    betrag_dtag_brutto = models.DecimalField(verbose_name='Betrag DTAG (brutto)', max_digits=7, decimal_places=2)
    fixkosten = models.DecimalField(verbose_name='Fixkosten (brutto)', max_digits=7, decimal_places=2)
    variable_kosten = models.DecimalField(verbose_name='variable Kosten (brutto)', max_digits=7, decimal_places=2)
    drittanbieterkosten = models.DecimalField(verbose_name='Drittanbieterkosten (brutto)', max_digits=7, decimal_places=2)
    summe_komplett_brutto = models.DecimalField(verbose_name='Rechnungssumme (brutto)', max_digits=7, decimal_places=2)
    grunddaten =  models.ForeignKey(InvoiceGrunddaten, on_delete=models.CASCADE)
    objects = customQuerySet.as_manager()

class InvoiceRechnungsPositionen(models.Model):
    kartennummer = models.CharField(max_length=25,verbose_name='Kartennummer',null=True, blank=True)
    kostenstelle = models.ForeignKey(Kostenstelle, on_delete=models.SET_NULL, null=True, blank=True)
    kostenstellennutzer = models.CharField(max_length=80,verbose_name='Kostenstellennutzer',null=True, blank=True)
    rufnummer = models.CharField(max_length=25,verbose_name='Rufnummer',null=True, blank=True)
    rechnungsbereich = models.CharField(max_length=200,verbose_name='Rechnungsbereich',null=True, blank=True)
    rechnungsposition = models.CharField(max_length=200,verbose_name='Rechnungsposition',null=True, blank=True)
    menge = models.IntegerField(verbose_name='Menge',null=True, blank=True)
    infomenge = models.DecimalField(verbose_name='Infomenge', max_digits=12, decimal_places=2,null=True, blank=True)
    einheit = models.CharField(max_length=50,verbose_name='Einheit',null=True, blank=True)
    beginn_datum = models.DateTimeField(verbose_name='Beginn-Datum', null=True, blank=True)
    ende_datum = models.DateTimeField(verbose_name='Ende-Datum', null=True, blank=True)
    info_betrag = models.DecimalField(verbose_name='Info-Betrag', max_digits=7, decimal_places=2,null=True, blank=True)
    eur_netto = models.DecimalField(verbose_name='EUR (Netto)', max_digits=7, decimal_places=2,null=True, blank=True)
    summe_nettobetrag = models.DecimalField(verbose_name='Summen Nettobetrag', max_digits=7, decimal_places=2,null=True, blank=True)
    andere_leistungen_eur_brutto = models.DecimalField(verbose_name='Andere Leistungen EUR (brutto)', max_digits=7, decimal_places=2,null=True, blank=True)
    summen_brutto_betraege = models.DecimalField(verbose_name='Summen Brutto-beträge', max_digits=7, decimal_places=2,null=True, blank=True)
    grunddaten = models.ForeignKey(InvoiceGrunddaten, on_delete=models.CASCADE)
    objects = customQuerySet.as_manager()

class GutschriftFile(models.Model):
    data = models.FileField(validators=[validate_gutschrift, FileExtensionValidator(['xls'])])
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        uploaded_file = self.data.file

        super(GutschriftFile, self).save(*args, **kwargs)
        
        _cleaned_data = validate_or_process_gutschrift(uploaded_file)
        
        try:
            row = _cleaned_data.iloc[0]
            kostenstelle_id, _ = Kostenstelle.objects.get_or_create(kostenstelle=row['kostenstelle'])
            gs = Gutschrift.objects.create(
                from_file_id = self.id,
                gutschriftsnummer  = row['gutschriftsnummer'],
                rechnungsnummer  = row['rechnungsnummer'],
                kartennummer = row['kartennummer'],
                kostenstelle = kostenstelle_id,
                kostenstellennutzer = row['kostenstellennutzer'],
                rufnummer = row['rufnummer'],
                rechnungsposition = row['text'],
                eur_netto = row['eur_netto'],
                eur_brutto = row['eur_brutto'],
                grund = row['grund'],
            )

            id = InvoiceData.objects.get(grunddaten__rechnungsnummer = gs.rechnungsnummer, rufnummer = gs.rufnummer)
            id.variable_kosten = F('variable_kosten') + gs.eur_brutto
            id.betrag_dtag_brutto = F('betrag_dtag_brutto') + gs.eur_brutto
            id.summe_komplett_brutto = F('summe_komplett_brutto') + gs.eur_brutto
            rp = InvoiceRechnungsPositionen.objects.create(
                    kartennummer = gs.kartennummer,
                    kostenstelle = kostenstelle_id,
                    kostenstellennutzer = gs.kostenstellennutzer,
                    rufnummer = gs.rufnummer,
                    rechnungsbereich = "Gutschrift",
                    rechnungsposition = gs.rechnungsposition,
                    eur_netto = gs.eur_netto,
                    grunddaten = InvoiceGrunddaten.objects.get(rechnungsnummer = gs.rechnungsnummer),
            )
            id.save()
        
        except Exception as e:
            if self.data.file:
                if os.path.isfile(self.data.path):
                        os.remove(self.data.path)
            raise e
    
    class Meta:
        verbose_name = 'Gutschrift'
        verbose_name_plural = 'Gutschriften'

class Gutschrift(models.Model):
    gutschriftsnummer  = models.TextField(verbose_name='Gutschriftsnummer')
    from_file =  models.OneToOneField(GutschriftFile, on_delete=models.CASCADE)
    rechnungsnummer  = models.TextField(verbose_name='Rechnungsnummer')
    kartennummer = models.CharField(max_length=25,verbose_name='Kartennummer',null=True, blank=True)
    kostenstelle = models.ForeignKey(Kostenstelle, on_delete=models.SET_NULL, null=True, blank=True)
    kostenstellennutzer = models.CharField(max_length=80,verbose_name='Kostenstellennutzer',null=True, blank=True)
    rufnummer = models.CharField(max_length=25,verbose_name='Rufnummer',null=True, blank=True)
    rechnungsposition = models.CharField(max_length=200,verbose_name='Rechnungsposition',null=True, blank=True)
    eur_netto = models.DecimalField(verbose_name='EUR (Netto)', max_digits=7, decimal_places=2,null=True, blank=True)
    eur_brutto = models.DecimalField(verbose_name='EUR (Netto)', max_digits=7, decimal_places=2,null=True, blank=True)
    grund = models.CharField(max_length=200,verbose_name='Rechnungsposition',null=True, blank=True)
    objects = customQuerySet.as_manager()