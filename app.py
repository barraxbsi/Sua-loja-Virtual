import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configurações do Banco de Dados e Pasta de Upload
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Cria a pasta de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco = db.Column(db.Float, nullable=False)
    imagem_url = db.Column(db.String(255), nullable=True)
    estoque = db.Column(db.Integer, default=10)

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

@app.route('/admin')
def admin_index():
    produtos = Produto.query.all()
    return render_template('admin.html', produtos=produtos)

@app.route('/admin/cadastrar', methods=['POST'])
def admin_cadastrar():
    nome = request.form.get('nome')
    categoria = request.form.get('categoria')
    descricao = request.form.get('descricao')
    preco = float(request.form.get('preco'))
    estoque = int(request.form.get('estoque', 10))
    
    # Processamento da Imagem enviada do PC
    file = request.files.get('imagem_file')
    imagem_path = None
    
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        imagem_path = f'/static/uploads/{filename}'
    else:
        imagem_path = request.form.get('imagem_url') # Fallback para URL caso não envie arquivo

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
def admin_deletar(id):
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    return redirect(url_for('admin_index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)