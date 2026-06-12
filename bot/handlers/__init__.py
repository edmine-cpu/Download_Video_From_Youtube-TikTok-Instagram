from aiogram import Router
from .start import router as start_router
from .url import router as download_router


routers = [start_router, download_router]
main_router = Router()
main_router.include_routers(*routers)