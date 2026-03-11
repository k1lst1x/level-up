from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import RegisterForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    next_url = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if next_url and not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = ""

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = user.Role.CUSTOMER
            user.save()

            login(request, user)
            return redirect(next_url or "/")
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form, "next_url": next_url})
