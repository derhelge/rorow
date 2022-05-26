from django import forms
from .models import GutschriftFile, InvoiceFile, MasterReportFile

class InvoiceFileFormAdmin(forms.ModelForm):
    class Meta:
        model = InvoiceFile
        fields = '__all__'

class GutschriftFileFormAdmin(forms.ModelForm):
    class Meta:
        model = GutschriftFile
        fields = '__all__'

class MasterReportFileFormAdmin(forms.ModelForm):
    class Meta:
        model = MasterReportFile
        fields = '__all__'

