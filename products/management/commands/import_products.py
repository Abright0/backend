import os
from django.core.management.base import BaseCommand
from products.utils import import_products_from_xml

class Command(BaseCommand):
    help = "Import products from an XML file"

    def add_arguments(self, parser):
        parser.add_argument("xml_file", type=str, help="Path to the XML file")

    def handle(self, *args, **options):
        xml_file = options["xml_file"]

        if not os.path.exists(xml_file):
            self.stderr.write(self.style.ERROR(f"File not found: {xml_file}"))
            return

        result = import_products_from_xml(xml_file)

        if result["success"]:
            self.stdout.write(self.style.SUCCESS(result["message"]))
        else:
            self.stderr.write(self.style.ERROR(result["message"]))
