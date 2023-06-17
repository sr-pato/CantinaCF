from flask import flash, redirect, render_template, request, session, url_for, abort
from werkzeug.security import check_password_hash
from .settings import PERMISSIONS
from .db import get_user
from . import app


@app.route("/login", methods=("GET", "POST"))
def login():
    user_id = session["user_id"] if session.get("user_id") != "guest" else None
    if user_id is not None:
        flash(f"Você já está logado como {session['user']['name']}.", category="warning")
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = get_user(username, by="username")
        if user is None:
            flash("Usuário e/ou Senha incorretos.", category="error")
        elif not verify_password(password, user["password"]):
            flash("Usuário e/ou Senha incorretos.", category="error")
        else:
            login_user(user)
            flash("Você está logado com sucesso!", category="success")
            return redirect(url_for("profile"))
    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))


def verify_password(password, hashed_password):
    return check_password_hash(hashed_password, password)


def login_user(user):
    session["user_id"] = user["id"]
    session["user"] = dict(user)


@app.before_request
def check_permission():
    """Check user permission before each request"""
    current_user_id = session.get("user_id")
    if current_user_id is None: # the first request to the app
        set_guest_user() # set user_id to 'guest' in session
        flash("Você não está logado", category="warning")
        return redirect(url_for("login")) # redirect to login page
    
    if current_user_id == "guest" and not role_has_permission("guest"):
        flash("Você não está logado", category="warning")
        return redirect(url_for("login"))
    
    if current_user_id != "guest":
        user = get_user(current_user_id, by="id")
        session["user"] = dict(user)
        if user is None:
            abort(404) # user not found
        if not role_has_permission(user["role"]):
            abort(403) # user does not have permission

    if "cart" not in session:
        session["cart"] = []
    

def set_guest_user():
    """Set user_id to 'guest' in session"""
    session["user_id"] = "guest"


def role_has_permission(role):
    """Check if user has permission to access current endpoint"""
    permitted_endpoints = PERMISSIONS.get(role, [])
    return request.endpoint in permitted_endpoints