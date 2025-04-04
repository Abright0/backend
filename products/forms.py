# forms.py
from django import forms

class XMLUploadForm(forms.Form):
    xml_file = forms.FileField(label="Select an XML file")
