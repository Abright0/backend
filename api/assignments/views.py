from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny

from accounts.models import User
from assignments.models import Assignment
from .serializers import AssignmentSerializer

class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    # permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]