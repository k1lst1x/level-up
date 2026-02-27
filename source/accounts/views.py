from django.contrib.auth import login
from django.shortcuts import render, redirect

from .forms import RegisterForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = user.Role.CUSTOMER
            user.save()

            login(request, user)
            return redirect("/")
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form})
