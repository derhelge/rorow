from django.contrib import admin

from files.forms import GutschriftFileFormAdmin, InvoiceFileFormAdmin, MasterReportFileFormAdmin
from .models import GutschriftFile, InvoiceFile, MasterReportFile
from django.template.defaultfilters import date as _date

@admin.register(InvoiceFile)
class InvoiceFileAdmin(admin.ModelAdmin):
    form = InvoiceFileFormAdmin
    list_display = ('data', 'abrechnungszeit', 'Rahmenvertrag')

    @admin.display(description="Abrechnungszeit")
    def abrechnungszeit(self, obj):
        igd = obj.invoicegrunddaten
        if igd.rechnungsmonat_komplett:
            return _date(igd.abrechnungsperiode_start, "F Y")
        else:
            return "%s - %s" % (igd.abrechnungsperiode_start.strftime('%d.%m.%Y'),igd.abrechnungsperiode_ende.strftime('%d.%m.%Y'))
    def Rahmenvertrag(self, obj):
        return obj.invoicegrunddaten.rahmenvertragsnummer

@admin.register(GutschriftFile)
class GutschriftFileAdmin(admin.ModelAdmin):
    form = GutschriftFileFormAdmin

@admin.register(MasterReportFile)
class MasterReportFileAdmin(admin.ModelAdmin):
    form = MasterReportFileFormAdmin
