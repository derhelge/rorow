from datetime import datetime,timedelta
import ntpath
import pytz
import logging
import re
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def is_month_complete(start,end):
    if end.month == (end + timedelta(days=1)).month:
        return False
    if start.day == 1:
        return True
    else:
        return False

def _clean_grunddaten_from_sheet(sheets):
    rechnung_grunddaten = {}

    kad = sheets['Kunden-Absender Daten']

    rechnung_grunddaten['rechnungsnummer'] = kad[kad['key'] == 'Rechnungsnummer:'].value.item()
    rechnung_grunddaten['rahmenvertragsnummer'] = kad[kad['key'] == 'Rahmenvertragsnummer:'].value.item()
    rechnung_grunddaten['umsatzsteuer'] = float(kad[kad['key'] == 'Umsatzsteuer:'].value.item()[:-2].replace(',','.'))

    rechnung_grunddaten['abrechnungsperiode_start'] = pytz.utc.localize(datetime.strptime(kad[kad['key'] == 'Beginn der Abrechnungsperiode:'].value.item(), '%d.%m.%Y'))
    rechnung_grunddaten['abrechnungsperiode_ende'] = pytz.utc.localize(datetime.strptime(kad[kad['key'] == 'Ende der Abrechnungsperiode:'].value.item(), '%d.%m.%Y'))
    rechnung_grunddaten['rechnungsmonat_komplett'] = is_month_complete(rechnung_grunddaten['abrechnungsperiode_start'],rechnung_grunddaten['abrechnungsperiode_ende'])

    rs = sheets['Rechnungssummen']

    rechnung_grunddaten['rechnung_betrag_dtag_netto'] = float(rs[rs['text'] == 'Betrag Telekom Deutschland GmbH']['summen_betrag_netto'].item())
    rechnung_grunddaten['rechnung_betrag_dtag_brutto'] = float(rs[rs['text'] == 'Betrag Telekom Deutschland GmbH']['brutto_betrag'].item())
    rechnung_grunddaten['rechnung_betrag_drittanbieter_brutto'] = float(rs[rs['text'] == 'Genutzte Angebote']['betrag'].sum())

    rechnung_grunddaten['rechnung_summe_netto'] = float(rs[(rs['text'] == 'Rechnungsbetrag') | (rs['text'] == 'Summe Betrag')]['summen_betrag_netto'].item())
    rechnung_grunddaten['rechnung_summe_brutto'] = float(rs[rs['text'] == 'Zu zahlender Betrag']['brutto_betrag'].item())

    rp = sheets['Rechnungspositionen']

    rechnung_grunddaten['rechnung_betrag_vda_brutto'] = rp[(rp['service'] == "VDA") & (rp['rechnungsbereich'] == "Telekom Deutschland GmbH")]['summen_nettobetrag'].sum()

    zusatzangaben = rp[rp['rechnungsbereich'] == "Zusatzangaben zum Rechnungsbetrag"]

    if not zusatzangaben['rechnungsposition'].empty:
        regex = r'^([0-9,]+)% Vergünstigung auf\s(.*)$'
        match = re.search(regex, zusatzangaben['rechnungsposition'].item())
        rechnung_grunddaten[f"rechnung_zusatzangaben_auf_rechnungsbereich"] = match.group(2)
        rechnung_grunddaten[f"rechnung_zusatzangaben_prozent"] = match.group(1)

    rechnung_grunddaten = pd.DataFrame(rechnung_grunddaten, index=[0])

    return rechnung_grunddaten

def _clean_summen_der_verguenstigungen(sheets):
    # Summen der Vergünstigen berechnen:
    # Erst alle Einzelpositionen zusammensetzen
    # und am Ende der Funktion aufsummieren

    rp_sheet = sheets['Rechnungspositionen']

    rp = rp_sheet[(rp_sheet['service'] == "Telefonie") 
                & (rp_sheet['eur_netto'].notnull()) 
                & (rp_sheet['summen_brutto_betraege'].isnull()) 
                & (rp_sheet['andere_leistungen_eur_brutto'].isnull())]

    df = pd.DataFrame()

    regex = r'^[0-9,]+% auf\s?(Grundpreis\s(.*)|(TwinBill - Aufpreis))$'
    tmp = rp['rechnungsposition'].str.extractall(regex).droplevel(-1)
    df['kartennummer'] = rp['kartennummer']
    df['rufnummer'] = rp['rufnummer']
    df['verguenstigung_grundpreis_art'] = tmp[1].combine_first(tmp[2])
    df['verguenstigung_grundpreis_art'].replace(['TwinBill - Aufpreis'], 'TwinBill Aufpreis', inplace=True)
    df['verguenstigung_grundpreis_summe'] = pd.to_numeric(rp['eur_netto'], errors='coerce')

    # Die Reihen ohne "verguenstigung_grundpreis_art" sind unvergünstigte Grundpreise
    # und müssen daher rausgefiltert werden für die Berechnung der vergünstigten Grundpreise
    df = df.dropna(axis=0)
    df = df.groupby(['kartennummer','rufnummer']).sum()

    return df

def _clean_berechne_echte_grundpreise_u_variable_kosten(sheets, df1):
    rp_sheet = sheets['Rechnungspositionen']

    # DTAG Kosten und errechneter Grundpreise inkl. Vergünstigungen
    # daraus dann können die variablen Kosten berechnet werden
    df2 = rp_sheet[(rp_sheet['service'] == "Telefonie")
                & (rp_sheet['summen_nettobetrag'].notnull())
                & (rp_sheet['kartennummer'].notna())]

    df2 = df2.groupby(['kartennummer','kostenstelle','kostenstellennutzer','rufnummer','rechnungsbereich'], dropna=False).sum()
    df2 = df2.reset_index()
    df2 = df2.pivot(index=['kartennummer','kostenstelle','kostenstellennutzer','rufnummer'], columns=['rechnungsbereich'], values='summen_nettobetrag')

    df2 = df2[['Grundpreise','Telekom Deutschland GmbH']]
    df2 = df2.reset_index()
    df2 = df2.set_index(['kartennummer','rufnummer'])
    df = pd.concat((df1, df2), axis=1)

    df = df.reset_index()

    cols = ['Grundpreise','Telekom Deutschland GmbH','verguenstigung_grundpreis_summe']
    df[cols] =df[cols].apply(pd.to_numeric, errors='coerce')
    df[cols] =df[cols].fillna(0)

    df['grundpreise_echt'] = df['Grundpreise']+df['verguenstigung_grundpreis_summe']
    df['variable_kosten'] = df['Telekom Deutschland GmbH'] - df['grundpreise_echt']
    df = df.drop(columns=['Grundpreise','verguenstigung_grundpreis_summe'])
    return df

def _rechnungspositionen_komplett(sheets):
    # Rechnungspositionen komplett importieren ohne zu bearbeiten
    rp = sheets['Rechnungspositionen']

    cols = ['beginn_datum','ende_datum']
    rp['beginn_datum'] = pd.to_datetime(rp['beginn_datum'],utc=True, format='%d.%m.%Y')
    rp['ende_datum'] = pd.to_datetime(rp['ende_datum'],utc=True, format='%d.%m.%Y')
    rp[cols] = rp[cols].astype(object)
    
    #rp = rp.where(pd.notnull(rp), None)
    rp = rp[rp['rufnummer'].notnull()]
    return rp


def _drittanbieterkosten(sheets):
    rp_sheet = sheets['Rechnungspositionen']

    df3 = rp_sheet[rp_sheet['summen_brutto_betraege'].notnull()]
    df3 = df3.rename(columns={'summen_brutto_betraege': 'drittanbieterkosten'})
    df3 = df3[['kartennummer','rufnummer','drittanbieterkosten']]
    df3 = df3.set_index(['kartennummer','rufnummer'])
    
    return df3['drittanbieterkosten']

def validate_or_process_invoice(data):
    head, tail = ntpath.split(data.name)
    filename = tail or ntpath.basename(data.name)
    file = data.file

    if not re.match(r'^Rechnung_',filename):
        raise ValueError(('Der Dateiname \"%s\" beginnt nicht mit \"Rechnung_\". Ist es wirklich eine Telekom-Rechnung?' % filename))
    sheets = pd.read_excel(file, sheet_name = None, dtype = object)
    if ('Kunden-Absender Daten' not in sheets):
        raise ValueError(('Das Excel-Sheet "Kunden-Absender Daten" fehlt.'))
    if ('Rechnungssummen' not in sheets):
        raise ValueError(('Das Excel-Sheet "Rechnungssummen" fehlt.'))
    if ('Rechnungspositionen' not in sheets):
        raise ValueError(('Das Excel-Sheet "Rechnungspositionen" fehlt.'))
    if ('Optionen' not in sheets):
        raise ValueError(('Das Excel-Sheet "Optionen" fehlt.'))

    sheets = pd.read_excel(file, sheet_name = None, dtype = object)

    # Umbenennen aller Spalten in allen Sheets
    sheets['Kunden-Absender Daten'] = sheets['Kunden-Absender Daten'].rename(columns={
        'Ihre Mobilfunk-Rechnung': "key",
        'Unnamed: 1': "value"
        }
    )
    sheets['Rechnungssummen'] = sheets['Rechnungssummen'].rename(columns={
        'Anbieter': 'anbieter',
        'Text': 'text',
        'Betrag': 'betrag',
        'Summen-betrag Netto': 'summen_betrag_netto',
        'USt-Betrag': 'ust_betrag',
        'Brutto-Betrag': 'brutto_betrag',
        }
    )

    sheets['Rechnungspositionen'] = sheets['Rechnungspositionen'].rename(columns={
        'Karten-/Profilnummer': 'kartennummer',
        'Kostenstelle': 'kostenstelle',
        'Kostenstellennutzer': 'kostenstellennutzer',
        'Rufnummer': 'rufnummer',
        'Service': 'service',
        'Rechnungsbereich': 'rechnungsbereich',
        'Rechnungsposition': 'rechnungsposition',
        'Menge': 'menge',
        'Infomenge': 'infomenge',
        'Einheit': 'einheit',
        'Beginn-Datum': 'beginn_datum',
        'Ende-Datum': 'ende_datum',
        'Info-Betrag': 'info_betrag',
        'EUR (Netto)': 'eur_netto',
        'Summen Nettobetrag': 'summen_nettobetrag',
        'Andere Leistungen EUR (brutto)': 'andere_leistungen_eur_brutto',
        'Summen Brutto-beträge': 'summen_brutto_betraege'
        }
    )

    sheets['Optionen'] = sheets['Optionen'].rename(columns={
        'Karten-/Profilnummer': 'kartennummer',
        'Rufnummer': 'rufnummer',
        'Dienst-bezeichnung': 'dienst_bezeichnung',
        'Option': 'option',
        'Bemerkung': 'bemerkung',
        'gültig ab': 'gueltig_ab',
        'gültig bis': 'gueltig_bis',
        }
    )

    # Alle numerischen Spalten in allen Sheets to_numeric wandeln
    cols = ['menge', 'infomenge', 'info_betrag',
            'eur_netto','summen_nettobetrag',
            'andere_leistungen_eur_brutto',
            'summen_brutto_betraege']

    sheets['Rechnungspositionen'][cols] = sheets['Rechnungspositionen'][cols].apply(pd.to_numeric, errors='coerce', axis=1)

    cols = ['betrag', 'summen_betrag_netto', 'ust_betrag', 'brutto_betrag']

    sheets['Rechnungssummen'][cols] = sheets['Rechnungssummen'][cols].apply(pd.to_numeric, errors='coerce', axis=1)

    # Datumsspalten in Datum konvertieren (UTC)

    sheets['Rechnungspositionen']['beginn_datum'] = pd.to_datetime(sheets['Rechnungspositionen']['beginn_datum'],utc=True, format='%d.%m.%Y')
    sheets['Rechnungspositionen']['ende_datum'] = pd.to_datetime(sheets['Rechnungspositionen']['ende_datum'],utc=True, format='%d.%m.%Y')
    sheets['Optionen']['gueltig_ab'] = pd.to_datetime(sheets['Optionen']['gueltig_ab'],utc=True, format='%d.%m.%Y')
    sheets['Optionen']['gueltig_bis'] = pd.to_datetime(sheets['Optionen']['gueltig_bis'],utc=True, format='%d.%m.%Y')

    rp = _rechnungspositionen_komplett(sheets)

    rechnung_grunddaten = _clean_grunddaten_from_sheet(sheets)
    sum_rabatt = _clean_summen_der_verguenstigungen(sheets)
    
    df = _clean_berechne_echte_grundpreise_u_variable_kosten(sheets,sum_rabatt)
    
    df = df.set_index(['kartennummer','rufnummer'])
    
    df['drittanbieterkosten'] = _drittanbieterkosten(sheets)
    df['drittanbieterkosten'] = df['drittanbieterkosten'].fillna(value=0)

    # Zusatzangaben & Mehrwertsteuer auf variable, Fixkosten und Summe anwenden
    if ('rechnung_zusatzangaben_auf_rechnungsbereich' in rechnung_grunddaten.columns):
        if(rechnung_grunddaten["rechnung_zusatzangaben_auf_rechnungsbereich"].item() == "Betrag Telekom Deutschland GmbH"):
            abzug = 1 - float(rechnung_grunddaten['rechnung_zusatzangaben_prozent'].item())/100
            df['variable_kosten'] = df['variable_kosten'] * abzug
            df['grundpreise_echt'] = df['grundpreise_echt'] * abzug
            df['Telekom Deutschland GmbH'] = df['Telekom Deutschland GmbH'] * abzug
            rechnung_grunddaten['rechnung_betrag_vda_brutto'] = rechnung_grunddaten['rechnung_betrag_vda_brutto'] * abzug

    if (rechnung_grunddaten["umsatzsteuer"].item()):
        steuer = 1 + float(rechnung_grunddaten['umsatzsteuer'].item())/100
        df['variable_kosten'] = df['variable_kosten'] * steuer
        df['grundpreise_echt'] = df['grundpreise_echt'] * steuer
        df['Telekom Deutschland GmbH'] = df['Telekom Deutschland GmbH'] * steuer
        rechnung_grunddaten['rechnung_betrag_vda_brutto'] = rechnung_grunddaten['rechnung_betrag_vda_brutto'] * steuer
    
    df['summe_komplett_brutto'] = df['Telekom Deutschland GmbH']+df['drittanbieterkosten']

    cols = ['Telekom Deutschland GmbH', 'grundpreise_echt', 'variable_kosten', 'drittanbieterkosten', 'summe_komplett_brutto']
    df[cols] = df[cols].fillna(0)

    # Überprüfung Einzelabweichungen
    df['einzel_abweichung'] = df['Telekom Deutschland GmbH'] - (df['variable_kosten'] + df['grundpreise_echt'])
    df['einzel_abweichung'] = df['einzel_abweichung'].abs()

    anzahl_einzel_abweichung = len(df[df['einzel_abweichung']> 1e-6])

    if (anzahl_einzel_abweichung):
        #print(df[df['einzel_abweichung']> 1e-6].round(2))
        raise ValueError("Rechnung konnte nicht importiert werden, da bei %i Positionen die Summe zwischen den berechneten Kosten (variable Kosten + Fixkosten) nicht mit den aus der Datei übereinstimmen" % anzahl_einzel_abweichung)
    df = df.drop(columns=['einzel_abweichung'])

    # Überprüfung Gesamtsumme
    rechnung_grunddaten['rechnung_summe_brutto_berechnet'] = round(df['summe_komplett_brutto'].sum() + rechnung_grunddaten['rechnung_betrag_vda_brutto'],2)
    abweichung = float(np.absolute(rechnung_grunddaten['rechnung_summe_brutto_berechnet'] - rechnung_grunddaten['rechnung_summe_brutto']))
    if (abweichung >= 0.02):
        raise ValueError("Rechnung konnte nicht importiert werden, da die maximale Abweichung (2 Cent) zwischen der berechneten und der importierten Gesamtsumme zu hoch ist: {:.2f} €".format(abweichung))
    
    # Überprüfung auf negative variable Kosten
    anzahl_negative_variable_kosten = len(df[df['variable_kosten']<-1e-6])
    if anzahl_negative_variable_kosten:
        raise ValueError("Rechnung konnte nicht importiert werden, da bei %i Positionen negative variable Kosten berechnet wurden" % anzahl_negative_variable_kosten)

    # Alle Checks OK
    # Liste von neuen DataFrames zusammensetzen für weitere Verarbeitung
    rechnung_grunddaten  = rechnung_grunddaten.reset_index()
    df = df.reset_index()
    rp = rp.reset_index()
    df_list = list()
    df_list.append(rechnung_grunddaten)

    df = df.round(2)
    # (SQLite | Django)? kennt kein NaN
    df = df.where(pd.notnull(df), None)
    
    rp = rp.replace({np.datetime64('NaT'): None})
    rp = rp.replace({np.nan: None})
    
    df_list.append(df)
    df_list.append(rp)
    
    return df_list


def validate_or_process_gutschrift(data):
    filename = data.name
    file = data.file
    
    if not re.match(r'^Gutschrift_',filename):
        raise ValueError(('Der Dateiname \"%s\" beginnt nicht mit \"Gutschrift_\". Ist es wirklich eine Telekom-Gutschrift?' % filename))
    sheets = pd.read_excel(file, sheet_name = None, dtype = object)
    if ('Kunden-Absender Daten' not in sheets):
        raise ValueError(('Das Excel-Sheet "Kunden-Absender Daten" fehlt.'))
    if ('Summen' not in sheets):
        raise ValueError(('Das Excel-Sheet "Summen" fehlt.'))
    if ('Zusatzangaben' not in sheets):
        raise ValueError(('Das Excel-Sheet "Rechnungspositionen" fehlt.'))
    if ('Grund der Gutschrift' not in sheets):
        raise ValueError(('Das Excel-Sheet "Optionen" fehlt.'))

    sheets = pd.read_excel(file, sheet_name = None, dtype = object)

    # Umbenennen aller Spalten in allen Sheets
    sheets['Kunden-Absender Daten'] = sheets['Kunden-Absender Daten'].rename(columns={
        'Ihre Mobilfunk-Gutschrift': "key",
        'Unnamed: 1': "value"
        }
    )
    sheets['Summen'] = sheets['Summen'].rename(columns={
        'Anbieter': 'anbieter',
        'Text': 'text',
        'Betrag': 'betrag',
        'Summen-betrag Netto': 'summen_betrag_netto',
        'USt-Betrag': 'ust_betrag',
        'Brutto-Betrag': 'brutto_betrag',
        }
    )

    sheets['Zusatzangaben'] = sheets['Zusatzangaben'].rename(columns={
        'Rechnungsnummer': 'rechnungsnummer',
        'Rechnungsdatum': 'rechnungsdatum',
        'Karten-/Profilnummer': 'kartennummer',
        'Kostenstelle': 'kostenstelle',
        'Kostenstellennutzer': 'kostenstellennutzer',
        'Rufnummer': 'rufnummer',
        'Text': 'text',
        'EUR (Netto)': 'eur_netto',
        'EUR (Brutto)': 'eur_brutto',
        }
    )

    sheets['Grund der Gutschrift'] = sheets['Grund der Gutschrift'].rename(columns={
        'Text': 'text',
        }
    )

    # Alle numerischen Spalten in allen Sheets to_numeric wandeln
    cols = ['betrag', 'summen_betrag_netto', 'ust_betrag',
            'brutto_betrag']
    sheets['Summen'][cols] = sheets['Summen'][cols].apply(pd.to_numeric, errors='coerce', axis=1)

    cols = ['eur_netto', 'eur_brutto']
    sheets['Zusatzangaben'][cols] = sheets['Zusatzangaben'][cols].apply(pd.to_numeric, errors='coerce', axis=1)

    # Datumsspalten in Datum konvertieren (UTC)
    sheets['Zusatzangaben']['rechnungsdatum'] = pd.to_datetime(sheets['Zusatzangaben']['rechnungsdatum'],utc=True, format='%d.%m.%Y')

    df = sheets['Kunden-Absender Daten']
    df = df.dropna()
    gs = dict(zip(df.key.str.replace(r':$', '', regex=True), df.value))
    gs['Gutschriftsdatum'] = pytz.utc.localize(datetime.strptime(gs['Gutschriftsdatum'], "%d.%m.%Y"))

    sheet_summen = sheets['Summen']

    # Check ob nur Telekom Gutschriften. Drittanbieter-Gutschriften werden nicht beruecksichtigt
    if not sheet_summen[(sheet_summen['anbieter']!="Telekom Deutschland GmbH")]['anbieter'].dropna().empty:
        _drittanbieter = sheet_summen[(sheet_summen['anbieter']!="Telekom Deutschland GmbH")]['anbieter'].dropna().to_json()
        raise ValueError('Die Gutschrift enhält nicht unterstützte Drittanbieter: "%s"' % _drittanbieter)

    _summen = sheet_summen[(sheet_summen['text']=="Gutschriftsbetrag inkl. Umsatzsteuer")][['summen_betrag_netto','ust_betrag','brutto_betrag']].to_dict('records')
    if _summen.__len__() > 1:
        raise ValueError('Die Gutschrift enhält %s Einzelgutschriften. Das wird nicht unterstützt' % _summen.__len__())
    gs.update(_summen[0])


    gz = sheets['Zusatzangaben']

    if len(gz.index) > 1:
        raise ValueError('Die Gutschrift enhält %s Einzelgutschriften. Das wird zur Zeit nicht unterstützt.' % len(gz.index))

    if gs['summen_betrag_netto'] != gz['eur_netto'].item():
        raise ValueError('Die Beträge in Zusatzangaben (%s) und Summen (%s) stimmen nicht überein.' % (gz['eur_netto'].item(), gs['summen_betrag_netto']))

    gz['gutschriftsnummer'] = gs['Gutschriftsnummer']
    gz['eur_brutto'] = gs['brutto_betrag']

    gz['grund'] = sheets['Grund der Gutschrift']['text'].item()
    return gz

def validate_or_process_masterreport(data):
    filename = data.name
    file = data.file
    #if DataFile.objects.filter(data=filename).exists():
    #    raise forms.ValidationError(('Die Datei "%s" wurde bereits hochgeladen' % filename), code='file_already_exists')
    if not re.match(r'^\d{4}\d{2}\d{2}',filename):
        raise ValueError(('Der Dateiname "%s" beginnt nicht mit einem Datum (Ymd). Ist es wirklich ein Masterreport?'), code='wrong_filename')
    sheets = pd.read_excel(file, sheet_name = None, dtype = object)
    if ('Kundennummer' not in sheets):
        raise ValueError(('Das Excel-Sheet "Kundennummer" fehlt. Ist es wirklich ein Masterreport?'), code='wrong_file')

    df = sheets['Kundennummer']
    auswahl_spalten = [
        'Rufnummer',
        'Kostenstelle',
        'Kostenstellennutzer',
        'GP/Organisationseinheit',
        'Rahmenvertrag',
        'Kundennummer',
        'Daten Optionen',
        'Voice Optionen',
        'Mischoptionen (Voice, Data, SMS)',
        'Mehrkarten Optionen',
        'Roaming Optionen',
        'Sonstige Optionen',
        'Karten-/Profilnummer',
        'EVN',
        'Vertragsbeginn',
        'Bindefristende',
        'Bindefrist',
        'Tarif',
        'Sperren',
        'Sperrgrund',
        'Stillegung',
        'Letzte Vertragsverlängerung',
        'VVL Grund',
        'VVL Berechtigung',
        'Kündigungstermin',
        'Kündigungseingang'
    ]
    df = df[auswahl_spalten]



    # Datumsspalten in Datum konvertieren (UTC)

    df['Vertragsbeginn']= pd.to_datetime(df['Vertragsbeginn'],utc=True, format='%d.%m.%Y')
    df['Bindefristende']= pd.to_datetime(df['Bindefristende'],utc=True, format='%d.%m.%Y')
    
    df.loc[:,'exported_at'] = pytz.utc.localize(datetime.strptime(re.match(r"(^\d{4}\d{2}\d{2})", filename).group(1),'%Y%m%d'))
    df['VVL Berechtigung'].replace('J','True',inplace=True)
    df['VVL Berechtigung'].replace('N','False',inplace=True)

    df =df.astype(object).where(df.notnull(), None)

    return df