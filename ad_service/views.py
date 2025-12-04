from django.shortcuts import render


def home(request):
    """Простое представление для главной страницы"""
    return render(request, "home.html")
