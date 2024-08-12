from fastapi import APIRouter, Request

from app.utils.forms import RegistrationForm, LoginForm


from .utils import templates

router = APIRouter()


@router.get("/", name="index")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/register", name="register")
async def register(request: Request):
    form = RegistrationForm()
    return templates.TemplateResponse("register.html", {"request": request, "form": form})


@router.get("/login", name="login")
async def login(request: Request):
    form = LoginForm()
    return templates.TemplateResponse("login.html", {"request": request, "form": form})
