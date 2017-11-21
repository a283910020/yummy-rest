"""RESTPLus API init"""
from flask_restplus import Api
from app import APP

API = Api(
    app=APP, version='1.0', title="Yummy REST",
    description="REST API implementation of the Yummy Recipes using Flask and PostgreSQL"
)
