# views.py
import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.management import call_command
from .forms import XMLUploadForm

def upload_xml(request):
    if request.method == "POST":
        form = XMLUploadForm(request.POST, request.FILES)
        if form.is_valid():
            xml_file = form.cleaned_data["xml_file"]

            # Save the file temporarily
            temp_file_path = os.path.join(settings.MEDIA_ROOT, "temp_import.xml")
            with open(temp_file_path, "wb+") as destination:
                for chunk in xml_file.chunks():
                    destination.write(chunk)

            try:
                # Option 1: Call your management command programmatically
                call_command("import_products", temp_file_path)
                messages.success(request, "Products imported successfully!")
            except Exception as e:
                messages.error(request, f"Error importing products: {e}")
            finally:
                # Remove the temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

            return redirect("upload_xml")
    else:
        form = XMLUploadForm()

    return render(request, "upload_xml.html", {"form": form})
