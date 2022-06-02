from django.db.models import Sum,Exists,OuterRef,F,Subquery,FloatField
from django.template.defaultfilters import date as _date
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import TruncDate
from .models import Gutschrift, InvoiceData, InvoiceGrunddaten, InvoiceRechnungsPositionen, Kostenstelle, MasterReportData

def _cost_development_for_number_chart(user,rufnummer):
    labels = []
    data_f = []
    data_v = []

    queryset = reversed(InvoiceData.objects.filter(rufnummer=rufnummer).managed_by_user(user)
                .values('grunddaten__abrechnungsperiode_start')
                .annotate(
                    fixkosten=Sum('fixkosten',output_field=FloatField()),
                    variable_kosten=Sum('variable_kosten',output_field=FloatField())
                    )
                .order_by('-grunddaten__abrechnungsperiode_start')[:12]
            )

    for entry in queryset:
        date_obj = _date(entry['grunddaten__abrechnungsperiode_start'], "F Y")
        labels.append(date_obj)
        data_f.append(round(entry['fixkosten'],2))
        data_v.append(round(entry['variable_kosten'],2))
    
    return {
        'labels': labels,
        'data_f': data_f,
        'data_v': data_v
    }

def _variable_costs_for_number_chart(user,rufnummer,year,month):

    labels = []
    data = []
    all_bg_colors= ['#5281bc', '#6d74b7', '#8866ab', '#9d5696', '#ab467b', '#d65b73','#f47a68']

    queryset = (InvoiceRechnungsPositionen.objects.managed_by_user(user).in_month(year,month)
        .filter(rufnummer=str(rufnummer))
        .filter(rechnungsbereich__in= ['Datenpässe',
            'Nutzungspreise GPRS / Daten',
            'Verbindungspreise MMS ServiceCenter',
            'Verbindungspreise Mobilbox',
            'Verbindungspreise SMS ServiceCenter',
            'Verbindungspreise Telefonie'])
        .filter(eur_netto__isnull=False)
        .annotate(brutto=Sum(F('eur_netto')*(1+(F('grunddaten__umsatzsteuer')/100.0)),output_field=FloatField()))
        .values('brutto','rechnungsposition','eur_netto').order_by('-eur_netto')
    )
    for obj in queryset:
        labels.append(obj['rechnungsposition'])
        data.append(round(obj['brutto'],2))

    return {
        'labels': labels,
        'data': data,
        'bg_colors': all_bg_colors
        }

def _cost_development_chart(user):
    labels = []
    data_f = []
    data_v = []

    queryset = reversed(InvoiceData.objects.managed_by_user(user)
                .values('grunddaten__abrechnungsperiode_start')
                .annotate(
                    fixkosten=Sum('fixkosten',output_field=FloatField()),
                    variable_kosten=Sum('variable_kosten',output_field=FloatField())
                    )
                .order_by('-grunddaten__abrechnungsperiode_start')[:12]
    )

    for entry in queryset:
        date_obj = _date(entry['grunddaten__abrechnungsperiode_start'], "F Y")
        labels.append(date_obj)
        data_f.append(round(entry['fixkosten'],2))
        data_v.append(round(entry['variable_kosten'],2))
    
    return {
        'labels': labels,
        'data_f': data_f,
        'data_v': data_v
    }

def _top10_phonenumber_costs_chart(user,year,month):

    labels = []
    data_f = []
    data_v = []

    queryset = (
            InvoiceData.objects.in_month(year,month).managed_by_user(user)
            .values('rufnummer').order_by('rufnummer')
            .annotate(
                fixkosten=Sum('fixkosten',output_field=FloatField()),
                variable_kosten=Sum('variable_kosten',output_field=FloatField()),
                gesamtkosten=Sum('summe_komplett_brutto',output_field=FloatField())
            )
            .order_by('-gesamtkosten')[:10]
            )
    
    for entry in queryset:
        labels.append(entry['rufnummer'])
        data_f.append(entry['fixkosten'])
        data_v.append(entry['variable_kosten'])
    
    return {
        'labels': labels,
        'data_f': data_f,
        'data_v': data_v
    }

class YearMonthUserNavMixin(object):
    def get_context_data(self, **kwargs):
        context = super(YearMonthUserNavMixin, self).get_context_data(**kwargs)
        user = self.request.user
        context['username'] = user.username

        year = self.kwargs.get('year', None)
        month = self.kwargs.get('month', None)

        if not year and not month:
            context['cur_date'] = InvoiceGrunddaten.objects.latest('abrechnungsperiode_ende').abrechnungsperiode_start
            year=context['cur_date'].year
            month=context['cur_date'].month
        else:
            context['cur_date'] = InvoiceGrunddaten.objects.in_month(year,month).latest('abrechnungsperiode_ende').abrechnungsperiode_start

        context['all_available_months']= (
            InvoiceGrunddaten.objects
                .order_by('-abrechnungsperiode_start').only('abrechnungsperiode_start')
                .filter(
                    Exists(
                        InvoiceData.objects.managed_by_user(user), job_id=OuterRef('pk')
                    )
                )
            )
        context['rufnummern'] = InvoiceData.objects.in_month(year,month).managed_by_user(user).values('rufnummer').distinct()

        return context

class DashboardView(YearMonthUserNavMixin,LoginRequiredMixin,TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        year = context['cur_date'].year
        month = context['cur_date'].month

        latest_own_masterreport = MasterReportData.objects.managed_by_user(user).latest('exported_at')
        context['total_item_vvl'] = (
            MasterReportData.objects.managed_by_user(user).filter(vvlberechtigung=True)
            .filter(kuendigungstermin__isnull=True)
            .filter(exported_at__date=TruncDate(latest_own_masterreport.exported_at)).count()
            )
        context['kostenstellen_sums'] = (
            InvoiceData.objects.in_month(year,month).managed_by_user(user)
                .values('grunddaten__rahmenvertragsnummer','grunddaten__rechnungsnummer','kostenstelle__kostenstelle')
                .annotate(summe=Sum('summe_komplett_brutto'))
            )
        context['gesamtkosten'] = context['kostenstellen_sums'].aggregate(gesamtkosten=Sum('summe'))['gesamtkosten']

        if user.is_superuser:
            context['verantwortliche_ks'] = Kostenstelle.objects.all().count()
        else:
            context['verantwortliche_ks'] = user.feuser.kostenstellen.all().count()

        context['verantwortliche_rufnummern'] = context['rufnummern'].count()

        context['kostenentwicklung'] = _cost_development_chart(user)
        context['kostentreiber'] = _top10_phonenumber_costs_chart(user,year,month)

        context['superuser_rechnungen'] = InvoiceGrunddaten.objects.in_month(year,month).values('rechnungsnummer','rechnung_summe_brutto')

        sq = InvoiceGrunddaten.objects.in_month(year,month).filter(rechnungsnummer=OuterRef('rechnungsnummer'))
        context['superuser_gutschriften'] = Gutschrift.objects.values('gutschriftsnummer','eur_brutto').filter(Exists(sq))

        return context

class RufnummernListView(YearMonthUserNavMixin,LoginRequiredMixin,TemplateView):
    template_name = 'rufnummern.html'
   
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        year = context['cur_date'].year
        month = context['cur_date'].month

        latest_own_masterreport = MasterReportData.objects.managed_by_user(user).latest('exported_at')
        mr_subquery = MasterReportData.objects.filter(exported_at__date=TruncDate(latest_own_masterreport.exported_at)).filter(rufnummer=OuterRef('rufnummer'))

        context['rufnummern_list'] = (
            InvoiceData.objects.in_month(year,month).managed_by_user(user)
            .values('rufnummer','kostenstellennutzer').order_by('rufnummer')
            .annotate(
                betrag_dtag_brutto=Sum('betrag_dtag_brutto'),
                fixkosten=Sum('fixkosten'),
                variable_kosten=Sum('variable_kosten'),
                drittanbieterkosten=Sum('drittanbieterkosten'),
                summe_komplett_brutto=Sum('summe_komplett_brutto'),
            ).annotate(
                kostenstelle=F('kostenstelle__kostenstelle'),
                vvlberechtigung=Subquery(mr_subquery.values('vvlberechtigung')),
                bindefristende=Subquery(mr_subquery.values('bindefristende')),
                kuendigungstermin=Subquery(mr_subquery.values('kuendigungstermin')),
                tarif=Subquery(mr_subquery.values('tarif')),
            )
            .order_by('-summe_komplett_brutto'))

        return context

class RufnummerRechnungsPositionenListView(YearMonthUserNavMixin,LoginRequiredMixin,TemplateView):
    template_name = 'teilnehmer.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        year = context['cur_date'].year
        month = context['cur_date'].month

        context['all_available_months'] = (
            InvoiceData.objects.filter(rufnummer=str(self.kwargs['rufnummer']))
            .managed_by_user(user)
            .values('grunddaten__abrechnungsperiode_start')
            .order_by('-grunddaten__abrechnungsperiode_start')
        )       
        
        context['rechnungspositionen'] = (InvoiceRechnungsPositionen.objects.filter(rufnummer=str(self.kwargs['rufnummer']))
                .in_month(year,month).managed_by_user(user)
                .annotate(
                    rechnungsnummer=F('grunddaten__rechnungsnummer'),
                    )
            )

        context['summen_list'] = (
            InvoiceData.objects.managed_by_user(user)
            .in_month(year,month)
            .filter(rufnummer=str(self.kwargs['rufnummer']))
            .values('rufnummer')
            .annotate(
                betrag_dtag_brutto=Sum('betrag_dtag_brutto'),
                fixkosten=Sum('fixkosten'),
                variable_kosten=Sum('variable_kosten'),
                drittanbieterkosten=Sum('drittanbieterkosten'),
                summe_komplett_brutto=Sum('summe_komplett_brutto'),
                )
            )
                                    
        context['rechnungsdaten'] = (
            InvoiceData.objects.managed_by_user(user)
            .in_month(year,month)
            .filter(rufnummer=str(self.kwargs['rufnummer']))
            .values(
                'rufnummer',
                'kostenstellennutzer',
                'kostenstelle__kostenstelle',
                'grunddaten__rahmenvertragsnummer',
                'grunddaten__rechnungsnummer',
                'grunddaten__abrechnungsperiode_start',
                'grunddaten__abrechnungsperiode_ende'
                )
            )

        context['variable_kosten_rufnumer'] = _variable_costs_for_number_chart(user,str(self.kwargs['rufnummer']),year,month)
        context['kostenentwicklung_rufnumer'] = _cost_development_for_number_chart(user,str(self.kwargs['rufnummer']))

        latest_own_masterreport = MasterReportData.objects.latest('exported_at')
        context['vertragsdaten'] = MasterReportData.objects.filter(exported_at__date=TruncDate(latest_own_masterreport.exported_at)).filter(rufnummer=str(self.kwargs['rufnummer']))

        return context