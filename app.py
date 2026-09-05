import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configurações do Banco de Dados e Uploads
app.config['SECRET_KEY'] = 'chave_secreta_super_segura_aqui'  # Necessário para gerenciar sessões
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# --- MODELOS DO BANCO DE DADOS ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='cliente') # Perfil: 'cliente', 'admin', 'master'

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco = db.Column(db.Float, nullable=False)
    imagem_url = db.Column(db.String(255), nullable=True)
    estoque = db.Column(db.Integer, default=10)

# --- DECORATORS DE SEGURANÇA ---

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] not in ['admin', 'master']:
            flash('Acesso restrito ao painel administrativo.', 'danger')
            return redirect(url_for('login_admin'))
        return f(*args, **kwargs)
    return decorated_function

def master_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'master':
            flash('Ação restrita à Conta Mestre.', 'danger')
            return redirect(url_for('admin_index'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS DE AUTENTICAÇÃO E CONTA ---
# Rota de Cadastro de Clientes
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro_cliente():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('password')
        
        # Verifica se o e-mail já existe no banco
        usuario_existente = User.query.filter_by(email=email).first()
        if usuario_existente:
            flash('Este e-mail já está cadastrado. Tente fazer login.', 'warning')
            return redirect(url_for('login_cliente'))
        
        # Cria o novo cliente
        novo_cliente = User(
            nome=nome,
            email=email,
            password=generate_password_hash(senha),
            role='cliente'
        )
        
        db.session.add(novo_cliente)
        db.session.commit()
        
        flash('Cadastro realizado com sucesso! Faça login para continuar.', 'success')
        return redirect(url_for('login_cliente'))
        
    return render_template('cadastro.html')

@app.route('/login', methods=['GET', 'POST'])
def login_cliente():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('password')
        user = User.query.filter_by(email=email, role='cliente').first()
        
        if user and check_password_hash(user.password, senha):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_nome'] = user.nome
            return redirect(url_for('index'))
        flash('E-mail ou senha de cliente incorretos.', 'danger')
    return render_template('login_cliente.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('password')
        user = User.query.filter_by(email=email).filter(User.role.in_(['admin', 'master'])).first()
        
        if user and check_password_hash(user.password, senha):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_nome'] = user.nome
            return redirect(url_for('admin_index'))
        flash('Credenciais de administração inválidas.', 'danger')
    return render_template('login_admin.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- ROTAS DA LOJA (CLIENTE) ---

@app.route('/')
def index():
    categoria_filtro = request.args.get('categoria')
    busca = request.args.get('busca')
    
    query = Produto.query
    if categoria_filtro:
        query = query.filter_by(categoria=categoria_filtro)
    if busca:
        query = query.filter(Produto.nome.ilike(f'%{busca}%'))
        
    produtos = query.all()
    categorias = db.session.query(Produto.categoria).distinct().all()
    categorias_lista = [c[0] for c in categorias]

    return render_template('index.html', produtos=produtos, categorias=categorias_lista)

# --- ROTAS ADMINISTRATIVAS ---

@app.route('/admin')
@admin_required
def admin_index():
    produtos = Produto.query.all()
    return render_template('admin.html', produtos=produtos)

@app.route('/admin/cadastrar', methods=['POST'])
@admin_required
def admin_cadastrar():
    nome = request.form.get('nome')
    categoria = request.form.get('categoria')
    descricao = request.form.get('descricao')
    preco = float(request.form.get('preco'))
    estoque = int(request.form.get('estoque', 10))
    
    file = request.files.get('imagem_file')
    imagem_path = None
    
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        imagem_path = f'/static/uploads/{filename}'
    else:
        imagem_path = request.form.get('imagem_url')

    novo_produto = Produto(
        nome=nome,
        categoria=categoria,
        descricao=descricao,
        preco=preco,
        imagem_url=imagem_path,
        estoque=estoque
    )

    db.session.add(novo_produto)
    db.session.commit()

    return redirect(url_for('admin_index'))

@app.route('/admin/deletar/<int:id>')
@admin_required
def admin_deletar(id):
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    return redirect(url_for('admin_index'))

# Rota Exclusiva do Mestre para criar Administradores
@app.route('/admin/gerenciar-equipe', methods=['GET', 'POST'])
@master_required
def gerenciar_equipe():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Este e-mail já está em uso.', 'warning')
        else:
            novo_admin = User(
                nome=nome,
                email=email,
                password=generate_password_hash(senha),
                role='admin'
            )
            db.session.add(novo_admin)
            db.session.commit()
            flash(f'Administrador {nome} cadastrado com sucesso!', 'success')
            
    admins = User.query.filter_by(role='admin').all()
    return render_template('gerenciar_equipe.html', admins=admins)

# --- COMANDO CLI PARA CRIAR A SUA CONTA MESTRE ---

@app.cli.command("create-master")
def create_master():
    """Cria a Conta Mestre inicial no banco de dados"""
    db.create_all()
    email = "barral@admin.com"
    if not User.query.filter_by(email=email).first():
        master = User(
            nome="Administrador Mestre",
            email=email,
            password=generate_password_hash("suasenhasegura123"),
            role="master"
        )
        db.session.add(master)
        db.session.commit()
        print("Conta Mestre criada com sucesso! (E-mail: barral1@admin.com | Senha: Wagnerbarral3121)")
    else:
        print("A conta Mestre já existe no banco de dados.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)