from django.test import TestCase
import glob
from django.core.files.uploadedfile import SimpleUploadedFile
from .forms import InvoiceFileFormAdmin

class InvoiceTestCase(TestCase):
    def test_invoice_upload_and_process(self):
        files = sorted(glob.glob('./orig_files_for_tests/*.xls'))
        #files = glob.glob('/home/wiethoff/ownCloud/ro/Rechnung_18699327012681.xls')
        print("test")
        for f in files:
            print(f)
            with self.subTest():
                with open(f, 'rb') as file:
                    document = SimpleUploadedFile(file.name, file.read())
                form = InvoiceFileFormAdmin({},{'data': document})
                self.assertTrue(form.is_valid(),'%s: %s' % (str(f),str(form.errors.as_text)))

