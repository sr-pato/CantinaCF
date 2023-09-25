from flask import render_template, request, flash, session, redirect, url_for
from .models import Product, User, ProductSale, EditHistory, Page
from datetime import datetime, timedelta
from sqlalchemy.orm import aliased
from .auth import verify_password
from . import app, cache, db
from sqlalchemy import func
import hashlib


@app.route("/")
def index():
    """
    A function that handles the index route.
    """
    pages = Page.query.all()
    categories = {}
    for page in pages:
        if page.category_page.name not in categories:
            categories[page.category_page.name] = []
        categories[page.category_page.name].append(page)
    context = {
        "categories": categories,
    }
    return render_template("index.html", **context)

@app.route("/venda-produtos")
def cantina():
    """
    A function that handles the index route and the venda-produtos route.

    Returns:
        The rendered index.html template with the products as the context.
    """
    context = {
        "products": Product.query.order_by(Product.quantity.desc(), Product.name.asc()).all()
    }
    return render_template("cantina.html", **context)


@app.route("/venda-produtos/confirmar-compra", methods=["POST", "GET"])
def confirm_purchase():
    """
    A function that confirms a purchase by processing the purchase details and rendering the 'confirm-purchase.html' template.
    """
    if len(session["cart"]) == 0:
        flash("Nenhum produto adicionado ao carrinho para confirmação...", "error")
        return redirect(url_for("cantina"))
    if request.method == "POST":
        process_purchase(request.form)
    return render_template("confirm-purchase.html")


def process_purchase(form):
    """
    Process a purchase using the given form data.

    Args:
        form (dict): A dictionary containing the form data.
    """
    matricula = form.get("matricula")
    password = form.get("password")
    if None in (matricula, password):
        flash("Preencha todos os campos", "error")
        return
    
    user = User.query.filter((User.matricula == matricula) | (User.username == matricula) | (User.id == matricula)).first()
    if user is None:
        flash("Identificação (matrícula, id ou username) e/ou Senha incorretos...", "error")
        return
    
    if not verify_password(password, user.password):
        flash(f"Identificação (matrícula, id ou username) e/ou Senha incorretos...", "error")
        return
    
    total_compra = sum(product.value for product in session["cart"])
    if user.balance < total_compra:
        flash(f"O usuário {user.name} não tem saldo suficiente para realizar a compra... Seu saldo atual é de R$ {user.balance}", "error")
        return
    
    user.balance -= total_compra
    db.session.commit()

    for product in session["cart"]:
        new_product_sale = ProductSale(
            product_id=product.id,
            value=product.value,
            sold_to=user.id,
            sold_by=session["user"].id,
            status="to dispatch"
        )
        db.session.add(new_product_sale)
    db.session.commit()

    session["cart"] = []
    flash("Compra realizada com sucesso, dirija-se ao local de despachemento!", "success")


@app.route("/produtos")
def products():
    """
    A function that renders the 'products.html' template.
    """
    search = request.args.get("q", "")
    try:
        page = int(request.args.get("page"))
    except:
        page = 1
    try:
        per_page = int(request.args.get("per_page"))
    except:
        per_page = 10

    query = Product.query.filter((Product.name.ilike(f"%{search}%")) | (Product.description.ilike(f"%{search}%")))


    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    context = {
        "pagination": pagination,
    }

    return render_template("products.html", **context)

@app.route("/editar-produto", methods=["POST", "GET"])
def edit_product():
    product_id = request.args.get("product_id")
    if product_id is None:
        flash("Por favor, insira o ID do produto!", category="error")
        return redirect(url_for('products'))
    product = Product.query.filter_by(id=product_id).first()
    if product is None:
        flash("Produto de ID {} não encontrado!".format(product_id), category="error")
        return redirect(url_for('products'))
    
    if request.method == "POST":
        motivo = request.form.get("motivo")
        if motivo is None:
            flash("Por favor, insira o motivo, é obrigatório!", category="error")
            return redirect(url_for('edit_product', product_id=product_id))
        product_values = product.as_dict()
        for key, value in request.form.items():
            if key in (app.config["CSRF_COOKIE_NAME"], 'action', 'motivo'):
                continue
            old_value = str(product_values.get(key))
            if old_value != value:
                setattr(product, key, value)
                db.session.commit()
                edit_history = EditHistory(
                    edited_by=session["user"].id,
                    key=key,
                    old_value=old_value,
                    new_value=value,
                    reason=motivo,
                    object_type="product",
                    product_id=product_id
                )
                db.session.add(edit_history)
                db.session.commit()
                column = [c for c in product.__table__.columns if c.name == key][0]
                friendly_key_name = column.info.get("label", key)
                flash(f"Alteração de '{friendly_key_name}' foi feita com sucesso ({old_value} -> {value})!", category="success")
        
    context = {
        "product": Product.query.filter_by(id=product_id).first()
    }
    return render_template("edit-product.html", **context)


@app.route("/historico-vendas")
def sales_history():
    vendido_por = request.args.get("vendido_por", "")
    vendido_para = request.args.get("vendido_para", "")
    order_by = request.args.get("order_by", "id")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    order_mode = request.args.get("order_mode", "ASC")

    sold_by_user = aliased(User)
    sold_to_user = aliased(User)
    dispatched_by_user = aliased(User)

    query = db.session.query(ProductSale)

    if vendido_por or vendido_para:
        query = query.join(sold_by_user, ProductSale.sold_by == sold_by_user.id)
        query = query.join(sold_to_user, ProductSale.sold_to == sold_to_user.id)

    if vendido_por:
        query = query.filter((sold_by_user.username.contains(vendido_por)) | (sold_by_user.matricula.contains(vendido_por)))

    if vendido_para:
        query = query.filter((sold_to_user.username.contains(vendido_para)) | (sold_to_user.matricula.contains(vendido_para)))

    if start_date:
        start_date = datetime.strptime(start_date, "%d/%m/%Y")
    else:
        start_date = db.session.query(func.min(ProductSale.added_at)).scalar()

    if end_date:
        end_date = datetime.strptime(end_date, "%d/%m/%Y")
    else:
        end_date = db.session.query(func.max(ProductSale.added_at)).scalar()

    query = query.join(dispatched_by_user, ProductSale.dispatched_by == dispatched_by_user.id)
    query = query.join(Product, Product.id == ProductSale.product_id)

    query = query.filter(ProductSale.added_at.between(start_date, end_date))
    query = query.order_by(getattr(ProductSale, order_by).asc() if order_mode == "ASC" else getattr(ProductSale, order_by).desc())

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    results = pagination.items

    identificador = f"historico-vendas-{vendido_por}-{vendido_para}-{start_date}-{end_date}-{session['user'].id}"
    hashed_query = hashlib.sha256(identificador.encode("utf-8")).hexdigest()
    cache.set(hashed_query, {'identifier': identificador, 'data': query.all()})

    stats = {}
    for result in results:
        product = result.product
        product_name = product.name

        if product_name in stats:
            stats[product_name]['ammount'] += result.value
            stats[product_name]['quantity'] += 1
        else:
            stats[product_name] = {
                'id': product.id,
                'quantity': 1,
                'valor': result.value,
                'ammount': result.value,
            }

    context = {
        "results": results,
        "pagination": pagination,
        "page": page,
        "per_page": per_page,
        "result_id": hashed_query,
        "stats": stats
    }
    return render_template("sales-history.html", **context)


@app.route('/vendas-hoje')
def filter_today_sales():
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    today_str = today.strftime("%d/%m/%Y")
    tomorrow_str = tomorrow.strftime("%d/%m/%Y")
    args = request.args.copy()
    args.pop('page', None)
    args['start_date'] = today_str
    args['end_date'] = tomorrow_str
    return redirect(url_for('sales_history', **args))

@app.route("/produtos-para-despache")
def products_for_despache():
    return render_template("products-for-despache.html")