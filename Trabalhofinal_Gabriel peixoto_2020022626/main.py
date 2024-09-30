from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, PasswordField, SelectMultipleField, widgets, FileField, DecimalField, IntegerField
from wtforms.validators import DataRequired, NumberRange
import sqlite3
from werkzeug.utils import secure_filename
import os
import uuid

# Configurações básicas do app Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['UPLOAD_FOLDER'] = 'static/fotos'
app.config['UPLOAD_FOLDER_LOGO'] = 'static/logo'
Bootstrap5(app)

# Extensões permitidas para upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

# Função para conectar ao banco de dados
def connect_db():
    conn = sqlite3.connect('banco_tinder.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para verificar se o arquivo tem a extensão permitida
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Criação da tabela de desenvolvedores
def create_table():
    with connect_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS devs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        cel TEXT NOT NULL,
                        habilidades TEXT NOT NULL,
                        senha TEXT NOT NULL,
                        foto TEXT NOT NULL,
                        curriculo TEXT,
                        tem_experiencia TEXT
                        )''')
    conn.close()

# Criação da tabela de empresas
def create_empresa_table():
    with connect_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS empresas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome_empresa TEXT NOT NULL,
                        cnpj TEXT NOT NULL,
                        setor TEXT NOT NULL,
                        endereco TEXT NOT NULL,
                        email TEXT NOT NULL,
                        telefone TEXT NOT NULL,
                        senha TEXT NOT NULL,
                        logo TEXT,
                        habilidades TEXT,
                        horas_semanais INTEGER,
                        horas_diarias INTEGER,
                        salario_ofertado REAL,
                        experiencia_necessaria TEXT
                        )''')
    conn.close()

# Criação da tabela de matches
def create_matches_table():
    with connect_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dev_id INTEGER NOT NULL,
                        empresa_id INTEGER NOT NULL,
                        dev_status TEXT NOT NULL DEFAULT 'pending' CHECK(dev_status IN ('like', 'dislike', 'pending')),
                        empresa_status TEXT NOT NULL DEFAULT 'pending' CHECK(empresa_status IN ('like', 'dislike', 'pending')),
                        UNIQUE(dev_id, empresa_id)
                        )''')
    conn.close()

# Função para obter a próxima empresa para um desenvolvedor
def get_next_empresa_for_dev(dev_id):
    with connect_db() as conn:
        viewed_empresas = conn.execute('''SELECT empresa_id FROM matches WHERE dev_id = ? AND dev_status != 'pending' ''', (dev_id,)).fetchall()
        viewed_empresa_ids = [row[0] for row in viewed_empresas]
        if viewed_empresa_ids:
            placeholders = ','.join(['?'] * len(viewed_empresa_ids))
            query = f'''SELECT * FROM empresas WHERE id NOT IN ({placeholders}) LIMIT 1'''
            empresa = conn.execute(query, viewed_empresa_ids).fetchone()
        else:
            empresa = conn.execute('''SELECT * FROM empresas LIMIT 1''').fetchone()
    return [empresa] if empresa else []

# Função para obter o próximo desenvolvedor para uma empresa
def get_next_dev_for_empresa(empresa_id):
    with connect_db() as conn:
        viewed_devs = conn.execute('''SELECT dev_id FROM matches WHERE empresa_id = ? AND empresa_status != 'pending' ''', (empresa_id,)).fetchall()
        viewed_dev_ids = [row[0] for row in viewed_devs]
        if viewed_dev_ids:
            placeholders = ','.join(['?'] * len(viewed_dev_ids))
            query = f'''SELECT * FROM devs WHERE id NOT IN ({placeholders}) LIMIT 1'''
            dev = conn.execute(query, viewed_dev_ids).fetchone()
        else:
            dev = conn.execute('''SELECT * FROM devs LIMIT 1''').fetchone()
    return [dev] if dev else []

# Classe de formulário para cadastro de desenvolvedores
class DevForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired()])
    cel = StringField('Celular', validators=[DataRequired()])
    habilidades = SelectMultipleField(
        'Habilidades', 
        choices=[
            ('python', 'Python'),
            ('html', 'HTML'),
            ('java', 'Java'),
            ('javascript', 'JavaScript'),
            ('c', 'C'),
            ('c++', 'C++'),
            ('csharp', 'C#'),
            ('php', 'PHP'),
            ('ruby', 'Ruby'),
            ('sql', 'SQL')
        ],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False)
    )
    foto = FileField('Foto do Desenvolvedor')
    senha = PasswordField('Senha', validators=[DataRequired()])
    curriculo = FileField('Currículo')
    tem_experiencia = StringField('Tem Experiência', validators=[DataRequired()])
    submit = SubmitField('Cadastrar')

# Classe de formulário para editar perfil de desenvolvedores
class EditDevForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired()])
    cel = StringField('Celular', validators=[DataRequired()])
    habilidades = SelectMultipleField(
        'Habilidades',
        choices=[
            ('python', 'Python'),
            ('html', 'HTML'),
            ('java', 'Java'),
            ('javascript', 'JavaScript'),
            ('c', 'C'),
            ('c++', 'C++'),
            ('csharp', 'C#'),
            ('php', 'PHP'),
            ('ruby', 'Ruby'),
            ('sql', 'SQL')
        ],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False)
    )
    foto = FileField('Atualizar Foto do Desenvolvedor')
    curriculo = FileField('Atualizar Currículo')
    tem_experiencia = StringField('Tem Experiência', validators=[DataRequired()])
    submit = SubmitField('Salvar Alterações')

# Classe de formulário para cadastro de empresas
class EmpresaForm(FlaskForm):
    nome_empresa = StringField('Nome da Empresa', validators=[DataRequired()])
    cnpj = StringField('CNPJ', validators=[DataRequired()])
    setor = StringField('Setor de Atuação', validators=[DataRequired()])
    endereco = TextAreaField('Endereço', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired()])
    telefone = StringField('Telefone', validators=[DataRequired()])
    logo = FileField('Logo da Empresa')
    senha = PasswordField('Senha', validators=[DataRequired()])
    horas_semanais = IntegerField('Horas Semanais', validators=[DataRequired(), NumberRange(min=0)])
    horas_diarias = IntegerField('Horas Diárias', validators=[DataRequired(), NumberRange(min=0)])
    salario_ofertado = DecimalField('Salário Ofertado', validators=[DataRequired(), NumberRange(min=0)], places=2)
    experiencia_necessaria = StringField('Experiência Necessária', validators=[DataRequired()])
    habilidades = SelectMultipleField(
        'Habilidades Procuradas', 
        choices=[
            ('python', 'Python'),
            ('html', 'HTML'),
            ('java', 'Java'),
            ('javascript', 'JavaScript'),
            ('c', 'C'),
            ('c++', 'C++'),
            ('csharp', 'C#'),
            ('php', 'PHP'),
            ('ruby', 'Ruby'),
            ('sql', 'SQL')
        ],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False)
    )
    submit = SubmitField('Cadastrar Empresa')

# Classe de formulário para editar perfil de empresas
class EditEmpresaForm(FlaskForm):
    nome_empresa = StringField('Nome da Empresa', validators=[DataRequired()])
    cnpj = StringField('CNPJ', validators=[DataRequired()])
    setor = StringField('Setor de Atuação', validators=[DataRequired()])
    endereco = TextAreaField('Endereço', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired()])
    telefone = StringField('Telefone', validators=[DataRequired()])
    habilidades = SelectMultipleField(
        'Habilidades Procuradas',
        choices=[
            ('python', 'Python'),
            ('html', 'HTML'),
            ('java', 'Java'),
            ('javascript', 'JavaScript'),
            ('c', 'C'),
            ('c++', 'C++'),
            ('csharp', 'C#'),
            ('php', 'PHP'),
            ('ruby', 'Ruby'),
            ('sql', 'SQL')
        ],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False)
    )
    horas_semanais = IntegerField('Horas Semanais', validators=[DataRequired(), NumberRange(min=0)])
    horas_diarias = IntegerField('Horas Diárias', validators=[DataRequired(), NumberRange(min=0)])
    salario_ofertado = DecimalField('Salário Ofertado', validators=[DataRequired(), NumberRange(min=0)], places=2)
    experiencia_necessaria = StringField('Experiência Necessária', validators=[DataRequired()])
    logo = FileField('Atualizar Logo da Empresa')
    submit = SubmitField('Salvar Alterações')

# Rota principal (home)
@app.route("/")
def home():
    with connect_db() as conn:
        empresas = conn.execute('SELECT logo FROM empresas WHERE logo IS NOT NULL').fetchall()
    return render_template("index.html", empresas=empresas)

# Rota para login de desenvolvedor
@app.route("/dev/login", methods=["GET", "POST"])
def dev_login():
    if request.method == "POST":
        email = request.form['email']
        senha = request.form['senha']
        with connect_db() as conn:
            dev = conn.execute('SELECT * FROM devs WHERE email = ? AND senha = ?', (email, senha)).fetchone()
        if dev:
            return redirect(url_for('dev_profile', dev_id=dev['id']))
        else:
            return render_template("dev_login.html", error="Credenciais inválidas.")
    return render_template("dev_login.html")

# Rota para exibir perfil de desenvolvedor
@app.route("/dev/profile/<int:dev_id>")
def dev_profile(dev_id):
    with connect_db() as conn:
        dev = conn.execute('SELECT * FROM devs WHERE id = ?', (dev_id,)).fetchone()
    return render_template("dev_profile.html", dev=dev)

# Rota para exibir todas as empresas
@app.route("/empresas")
def show_empresas():
    with connect_db() as conn:
        empresas = conn.execute('SELECT * FROM empresas').fetchall()
    return render_template("empresas.html", empresas=empresas, dev_id=None)

# Rota para curtir um desenvolvedor por uma empresa
@app.route("/empresa/like/<int:dev_id>", methods=["POST"])
def empresa_like(dev_id):
    empresa_id = request.form.get('empresa_id')
    if not empresa_id:
        return redirect(url_for('empresa_login'))
    empresa_id = int(empresa_id)
    action = request.form.get('action') 
    
    with connect_db() as conn:
        match = conn.execute('''SELECT * FROM matches WHERE dev_id = ? AND empresa_id = ?''', (dev_id, empresa_id)).fetchone()
        dev = conn.execute('SELECT * FROM devs WHERE id = ?', (dev_id,)).fetchone()
        empresa = conn.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,)).fetchone()

        if match:
            conn.execute('''UPDATE matches SET empresa_status = ? WHERE dev_id = ? AND empresa_id = ?''', (action, dev_id, empresa_id))
        else:
            conn.execute('''INSERT INTO matches (dev_id, empresa_id, dev_status, empresa_status) VALUES (?, ?, ?, ?)''', (dev_id, empresa_id, 'pending', action))
        
        match = conn.execute('''SELECT * FROM matches WHERE dev_id = ? AND empresa_id = ?''', (dev_id, empresa_id)).fetchone()

        if match['dev_status'] == 'like' and match['empresa_status'] == 'like':
            flash(f"Parabéns! Você deu match com o desenvolvedor {dev['name']}!", 'match')
    
    return redirect(url_for('empresa_swipe', empresa_id=empresa_id))

# Rota para exibir próximos desenvolvedores para uma empresa curtir
@app.route("/empresa/swipe/<int:empresa_id>")
def empresa_swipe(empresa_id):
    devs = get_next_dev_for_empresa(empresa_id)
    with connect_db() as conn:
        empresa = conn.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,)).fetchone()
    if not devs:
        return render_template("nao_tem_devs.html", empresa=empresa)
    return render_template("devs.html", devs=devs, empresa_id=empresa_id, empresa=empresa)

# Rota para login de empresa
@app.route("/empresa/login", methods=["GET", "POST"])
def empresa_login():
    if request.method == "POST":
        cnpj = request.form['cnpj']
        senha = request.form['senha']
        with connect_db() as conn:
            empresa = conn.execute('SELECT * FROM empresas WHERE cnpj = ? AND senha = ?', (cnpj, senha)).fetchone()
        if empresa:
            return redirect(url_for('empresa_profile', empresa_id=empresa['id']))
        else:
            return render_template("empresa_login.html", error="Credenciais inválidas.")
    return render_template("empresa_login.html")

# Rota para exibir perfil de empresa
@app.route("/empresa/profile/<int:empresa_id>")
def empresa_profile(empresa_id):
    with connect_db() as conn:
        empresa = conn.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,)).fetchone()
    return render_template("empresa_profile.html", empresa=empresa)

# Rota para exibir todos os desenvolvedores
@app.route("/devs")
def show_devs():
    with connect_db() as conn:
        devs = conn.execute('SELECT * FROM devs').fetchall()
    return render_template("devs.html", devs=devs)

# Rota para curtir uma empresa por um desenvolvedor
@app.route("/dev/like/<int:empresa_id>", methods=["POST"])
def dev_like(empresa_id):
    dev_id = request.form.get('dev_id')
    if not dev_id:
        return redirect(url_for('dev_login'))
    dev_id = int(dev_id)
    action = request.form.get('action') 
    
    with connect_db() as conn:
        match = conn.execute('''SELECT * FROM matches WHERE dev_id = ? AND empresa_id = ?''', (dev_id, empresa_id)).fetchone()
        dev = conn.execute('SELECT * FROM devs WHERE id = ?', (dev_id,)).fetchone()
        empresa = conn.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,)).fetchone()

        if match:
            conn.execute('''UPDATE matches SET dev_status = ? WHERE dev_id = ? AND empresa_id = ?''', (action, dev_id, empresa_id))
        else:
            conn.execute('''INSERT INTO matches (dev_id, empresa_id, dev_status, empresa_status) VALUES (?, ?, ?, ?)''', (dev_id, empresa_id, action, 'pending'))
        
        match = conn.execute('''SELECT * FROM matches WHERE dev_id = ? AND empresa_id = ?''', (dev_id, empresa_id)).fetchone()

        if match['dev_status'] == 'like' and match['empresa_status'] == 'like':
            flash(f"Parabéns! Você deu match com a empresa {empresa['nome_empresa']}!", 'match')
    
    return redirect(url_for('dev_swipe', dev_id=dev_id))


# Rota para exibir próximas empresas para um desenvolvedor curtir
@app.route("/dev/swipe/<int:dev_id>")
def dev_swipe(dev_id):
    empresas = get_next_empresa_for_dev(dev_id)
    with connect_db() as conn:
        dev = conn.execute('SELECT * FROM devs WHERE id = ?', (dev_id,)).fetchone()
    if not empresas:
        return render_template("nao_tem_empresas.html", dev=dev)
    return render_template("empresas.html", empresas=empresas, dev_id=dev_id, dev=dev)

# Rota para registro de desenvolvedor
@app.route("/dev/register", methods=["GET", "POST"])
def dev_register():
    form = DevForm()
    if form.validate_on_submit():
        habilidades_selecionadas = ', '.join(form.habilidades.data)
        foto_filename = None
        curriculo_filename = None

        # Upload de foto
        if 'foto' in request.files:
            file = request.files['foto']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                extension = os.path.splitext(filename)[1]
                unique_filename = f"dev_{uuid.uuid4()}{extension}"
                foto_filename = unique_filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], foto_filename))

        # Upload de currículo
        if 'curriculo' in request.files:
            file = request.files['curriculo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                extension = os.path.splitext(filename)[1]
                unique_filename = f"curriculo_{uuid.uuid4()}{extension}"
                curriculo_filename = unique_filename
                file.save(os.path.join('static/curriculos', curriculo_filename))

        with connect_db() as conn:
            conn.execute('''INSERT INTO devs (name, email, cel, habilidades, senha, foto, curriculo, tem_experiencia)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                         (form.name.data, form.email.data, form.cel.data, habilidades_selecionadas, form.senha.data, foto_filename, curriculo_filename, form.tem_experiencia.data))
        return redirect(url_for('home'))
    return render_template("dev_register.html", form=form)

# Rota para edição de perfil de desenvolvedor
@app.route("/dev/profile/edit/<int:dev_id>", methods=["GET", "POST"])
def edit_dev_profile(dev_id):
    with connect_db() as conn:
        dev = conn.execute('SELECT * FROM devs WHERE id = ?', (dev_id,)).fetchone()

    form = EditDevForm()

    if request.method == 'GET':
        form.name.data = dev['name']
        form.email.data = dev['email']
        form.cel.data = dev['cel']
        form.habilidades.data = dev['habilidades'].split(', ')
        form.tem_experiencia.data = dev['tem_experiencia']
    elif form.validate_on_submit():
        habilidades_selecionadas = ', '.join(form.habilidades.data)
        foto_filename = dev['foto']
        curriculo_filename = dev['curriculo']
        if 'foto' in request.files and request.files['foto'].filename != '':
            file = request.files['foto']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                extension = os.path.splitext(filename)[1]
                unique_filename = f"dev_{uuid.uuid4()}{extension}"
                foto_filename = unique_filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], foto_filename))
        if 'curriculo' in request.files and request.files['curriculo'].filename != '':
            file = request.files['curriculo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                extension = os.path.splitext(filename)[1]
                unique_filename = f"curriculo_{uuid.uuid4()}{extension}"
                curriculo_filename = unique_filename
                file.save(os.path.join('static/curriculos', curriculo_filename))

        with connect_db() as conn:
            conn.execute('''
                UPDATE devs
                SET name = ?, email = ?, cel = ?, habilidades = ?, foto = ?, curriculo = ?, tem_experiencia = ?
                WHERE id = ?
            ''', (form.name.data, form.email.data, form.cel.data, habilidades_selecionadas, foto_filename, curriculo_filename, form.tem_experiencia.data, dev_id))
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('dev_profile', dev_id=dev_id))

    return render_template('edit_dev_profile.html', form=form, dev_id=dev_id)

# Rota para registro de empresa
@app.route("/empresa/register", methods=["GET", "POST"])
def empresa_register():
    form = EmpresaForm()
    if form.validate_on_submit():
        habilidades_selecionadas = ', '.join(form.habilidades.data)
        logo_filename = None
        if 'logo' in request.files:
            file = request.files['logo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                extension = os.path.splitext(filename)[1]
                unique_filename = f"empresa_{uuid.uuid4()}{extension}"
                logo_filename = unique_filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER_LOGO'], logo_filename))
        
        with connect_db() as conn:
            conn.execute('''INSERT INTO empresas (nome_empresa, cnpj, setor, endereco, email, telefone, senha, logo, habilidades, horas_semanais, horas_diarias, salario_ofertado, experiencia_necessaria)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (form.nome_empresa.data, form.cnpj.data, form.setor.data, form.endereco.data, 
                  form.email.data, form.telefone.data, form.senha.data, logo_filename, habilidades_selecionadas,
                  form.horas_semanais.data, form.horas_diarias.data, float(form.salario_ofertado.data), form.experiencia_necessaria.data))
        return redirect(url_for('home'))
    return render_template("empresa_register.html", form=form)

# Rota para edição de perfil de empresa
@app.route("/empresa/profile/edit/<int:empresa_id>", methods=["GET", "POST"])
def edit_empresa_profile(empresa_id):
    with connect_db() as conn:
        empresa = conn.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,)).fetchone()
    form = EditEmpresaForm()
    if request.method == 'GET':
        form.nome_empresa.data = empresa['nome_empresa']
        form.cnpj.data = empresa['cnpj']
        form.setor.data = empresa['setor']
        form.endereco.data = empresa['endereco']
        form.email.data = empresa['email']
        form.telefone.data = empresa['telefone']
        form.habilidades.data = empresa['habilidades'].split(', ') if empresa['habilidades'] else []
        form.horas_semanais.data = empresa['horas_semanais']
        form.horas_diarias.data = empresa['horas_diarias']
        form.salario_ofertado.data = empresa['salario_ofertado']
        form.experiencia_necessaria.data = empresa['experiencia_necessaria']
    elif form.validate_on_submit():
        habilidades_selecionadas = ', '.join(form.habilidades.data)
        logo_filename = empresa['logo']
        if 'logo' in request.files and request.files['logo'].filename != '':
            file = request.files['logo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                extension = os.path.splitext(filename)[1]
                unique_filename = f"empresa_{uuid.uuid4()}{extension}"
                logo_filename = unique_filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER_LOGO'], logo_filename))

        with connect_db() as conn:
            conn.execute('''
                UPDATE empresas
                SET nome_empresa = ?, cnpj = ?, setor = ?, endereco = ?, email = ?, telefone = ?, habilidades = ?, logo = ?, horas_semanais = ?, horas_diarias = ?, salario_ofertado = ?, experiencia_necessaria = ?
                WHERE id = ?
            ''', (form.nome_empresa.data, form.cnpj.data, form.setor.data, form.endereco.data,
                form.email.data, form.telefone.data, habilidades_selecionadas, logo_filename,
                form.horas_semanais.data, form.horas_diarias.data, float(form.salario_ofertado.data), form.experiencia_necessaria.data, empresa_id))
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('empresa_profile', empresa_id=empresa_id))

    return render_template('edit_empresa_profile.html', form=form, empresa_id=empresa_id)

# Rota para exibir matches de desenvolvedor
@app.route("/dev/matches/<int:dev_id>")
def dev_matches(dev_id):
    with connect_db() as conn:
        matches = conn.execute('''
            SELECT empresas.* FROM matches
            JOIN empresas ON matches.empresa_id = empresas.id
            WHERE matches.dev_id = ? AND matches.dev_status = 'like' AND matches.empresa_status = 'like'
        ''', (dev_id,)).fetchall()
    return render_template("dev_matches.html", matches=matches, dev_id=dev_id)

# Rota para exibir matches de empresa
@app.route("/empresa/matches/<int:empresa_id>")
def empresa_matches(empresa_id):
    with connect_db() as conn:
        matches = conn.execute('''
            SELECT devs.* FROM matches
            JOIN devs ON matches.dev_id = devs.id
            WHERE matches.empresa_id = ? AND matches.dev_status = 'like' AND matches.empresa_status = 'like'
        ''', (empresa_id,)).fetchall()
    return render_template("empresa_matches.html", matches=matches, empresa_id=empresa_id)

# Rota para exibir a página "Fale Conosco"
@app.route("/fale_conosco", methods=["GET", "POST"])
def fale_conosco():
    if request.method == "POST":
        nome = request.form['nome']
        email = request.form['email']
        mensagem = request.form['mensagem']
        flash('Sua mensagem foi enviada com sucesso!', 'success')
        return redirect(url_for('fale_conosco'))
    return render_template("fale_conosco.html")

# Iniciar o servidor e criar tabelas ao iniciar
if __name__ == '__main__':
    create_table()
    create_empresa_table()
    create_matches_table()
    app.run(debug=True, port=6001)
