import xml.etree.ElementTree as ET
from products.models import Product

def import_products_from_xml(xml_file_path):
    """Process XML file and import products into the database."""
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        for item in root.findall(".//item", namespaces={"g": "http://base.google.com/ns/1.0"}):
            product_id = get_element_text(item, "g:id")
            name = get_element_text(item, "title")
            description = get_element_text(item, "description")
            price = get_element_text(item, "g:price", float)
            image_link = get_element_text(item, "g:image_link")
            quantity = get_element_text(item, "g:quantity", int)
            availability = get_element_text(item, "g:availability")
            mpn = get_element_text(item, "g:mpn")
            gtin = get_element_text(item, "g:gtin")
            brand = get_element_text(item, "g:brand")
            shipping_weight = get_element_text(item, "g:shipping_weight")
            google_product_category = get_element_text(item, "g:google_product_category")
            product_type = get_element_text(item, "g:product_type")
            product_link = get_element_text(item, "link")

            Product.objects.update_or_create(
                google_id=product_id,
                defaults={
                    "name": name,
                    "description": description,
                    "price": price,
                    "image_link": image_link,
                    "quantity": quantity,
                    "availability": availability,
                    "mpn": mpn,
                    "gtin": gtin,
                    "brand": brand,
                    "shipping_weight": shipping_weight,
                    "google_product_category": google_product_category,
                    "product_type": product_type,
                    "link": product_link,
                },
            )
        return {"success": True, "message": "Products imported successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def get_element_text(item, tag_name, cast_type=str):
    element = item.find(tag_name)
    if element is not None and element.text:
        try:
            return cast_type(element.text.strip())
        except ValueError:
            return None
    return None
