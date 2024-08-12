from fastapi import APIRouter, Request

from app.utils.forms import RegistrationForm, LoginForm
from app.dependencies import CurrentUserForPage


from .utils import templates

router = APIRouter()


@router.get("/", name="index")
async def index(request: Request, current_user: CurrentUserForPage):
    username = current_user.username if current_user else None
    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": username,
    })


@router.get("/register", name="page:register")
async def register(request: Request):
    form = RegistrationForm()
    return templates.TemplateResponse("register.html", {"request": request, "form": form})


@router.get("/login", name="page:login")
async def login(request: Request):
    form = LoginForm()
    return templates.TemplateResponse("login.html", {"request": request, "form": form})
