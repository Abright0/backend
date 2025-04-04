from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from products.models import Product
from .serializers import ProductSerializer

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

import os
from django.conf import settings
from products.utils import import_products_from_xml

from fuzzywuzzy import fuzz

class ProductListCreate(APIView):
    def get(self, request):
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ProductImportView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure file is an XML file
        if not file_obj.name.lower().endswith('.xml'):
            return Response({"error": "Only .xml files are allowed"}, status=status.HTTP_400_BAD_REQUEST)

        # Save file temporarily
        file_path = os.path.join(settings.MEDIA_ROOT, "uploads", file_obj.name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Chunking file
        with open(file_path, "wb+") as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        # Process file
        result = import_products_from_xml(file_path)

        # Remove file after processing
        os.remove(file_path)

        return Response(result, status=status.HTTP_200_OK if result["success"] else status.HTTP_500_INTERNAL_SERVER_ERROR)

class SearchProductView(APIView):
    """
    Search the closest matching product. Based on 'q' param.
    """
    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {"error": "Query parameter 'q' is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Fetch all products from the database
        products = Product.objects.all()
        matches = []

        # Calculate a fuzzy matching score for each product name
        for product in products:
            if product.name:
                # token_set_ratio handles partial matches and token ordering
                score = fuzz.token_set_ratio(query.lower(), product.name.lower())
                matches.append((score, product))
        
        # Sort matches in descending order of score and get the top 5
        matches.sort(key=lambda x: x[0], reverse=True)
        top_matches = [product for score, product in matches[:5]]

        # Serialize the top matched products and return them
        serializer = ProductSerializer(top_matches, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)