from django.shortcuts import render
from datetime import date
from decimal import Decimal
from django.http import HttpResponse
from .services.reports import generate_remittance_pdf


def home(request):
    return render(request, "home.html")


# Create your views here.
