def theme(request):
    if request.user.is_authenticated:
        return {"theme": request.user.theme}
    return {"theme": request.COOKIES.get("theme", "system")}
