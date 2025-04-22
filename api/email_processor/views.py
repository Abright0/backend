# backend/api/email_processor/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import EmailDataSerializer

class ReceiveEmailView(APIView):
    print("Hit /api/receive-email/")

    def post(self, request, format=None):
        serializer = EmailDataSerializer(data=request.data)
        if serializer.is_valid():
            # Process logic
            print(f"Received email from: {serializer.validated_data['sender']}")
            return Response({"message": "Email data received successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)