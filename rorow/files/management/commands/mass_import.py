import glob
from django.core.management.base import BaseCommand
from files.forms import InvoiceFileFormAdmin

from django.core.files import File


class Command(BaseCommand):
    help = 'Mass Upload and process Files'


    def handle(self, *args, **options):
        files = sorted(glob.glob('Rechnung_*.xls'))
        for f in files:
            with open(f,'rb') as file:
                form = InvoiceFileFormAdmin({},{'data': File(file)})
                if form.is_valid():
                    print(str(file) + ": is valid")
                    form.save()
                else:
                    print(str(file) + ":" + str(form.errors.as_text))
