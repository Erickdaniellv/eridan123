

# app/routes/legal.py
from flask import Blueprint, request, render_template, flash, redirect, url_for, current_app
from app import csrf
from urllib.parse import  quote
from flask_login import  current_user, login_required
from app.forms import  ContratoForm
from datetime import datetime
from flask import Blueprint, make_response

leal_bp = Blueprint('leal', __name__)    


