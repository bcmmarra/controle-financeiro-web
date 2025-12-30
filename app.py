from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from datetime import datetime, timedelta

import locale
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
except:
    locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    
app = Flask(__name__)
app.secret_key = 'uma_chave_muito_segura_aqui'

@app.context_processor
def inject_now():
    return {'agora': datetime.now()}

# CONFIGURAÇÃO DO SEU BANCO (Ajuste a senha!)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Dc524876_*',
    'database': 'controle_financeiro'
}

@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    nome = request.form.get('nome')
    email = request.form.get('email')
    senha = request.form.get('senha')
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Insere o novo usuário
        sql = "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)"
        cursor.execute(sql, (nome, email, senha))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return redirect(url_for('login')) # Após cadastrar, vai para o login
    except Exception as e:
        return f"Erro ao cadastrar: {str(e)}"

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    msg = None

    if request.method == 'POST':
        novo_nome = request.form.get('nome')
        novo_email = request.form.get('email')
        nova_senha = request.form.get('senha')
        
        # Atualiza no banco
        cursor.execute("""
            UPDATE usuarios SET nome = %s, email = %s, senha = %s 
            WHERE id = %s
        """, (novo_nome, novo_email, nova_senha, session['usuario_id']))
        conn.commit()
        
        # Atualiza a sessão para o nome mudar no menu lateral/topo
        session['usuario_nome'] = novo_nome
        msg = "Dados atualizados com sucesso!"

    # Busca os dados atuais para preencher o form
    cursor.execute("SELECT nome, email, senha FROM usuarios WHERE id = %s", (session['usuario_id'],))
    usuario = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('perfil.html', usuario=usuario, mensagem=msg)

@app.route('/excluir_conta', methods=['POST'])
def excluir_conta():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['usuario_id']
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 1. Excluir todas as transações deste usuário
        cursor.execute("DELETE FROM transacoes WHERE usuario_id = %s", (user_id,))
        
        # 2. Excluir o usuário (Nota: Se você tiver categorias vinculadas apenas a ele, exclua-as também aqui)
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (user_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Limpar a sessão e mandar para o login
        session.clear()
        return redirect(url_for('login'))
        
    except Exception as e:
        return f"Erro ao excluir conta: {str(e)}"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE email = %s AND senha = %s", (email, senha))
        usuario = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', erro="E-mail ou senha incorretos")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['usuario_id']
    hoje = datetime.now()
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # --- CONSULTA 1: Total do Mês ---
    cursor.execute("""
        SELECT SUM(valor_total) as total 
        FROM transacoes 
        WHERE usuario_id = %s AND MONTH(data_transacao) = %s AND YEAR(data_transacao) = %s
    """, (user_id, hoje.month, hoje.year))
    gasto_mes = cursor.fetchone()['total'] or 0.0

    # --- CONSULTA 2: Próxima Conta ---
    cursor.execute("""
        SELECT descricao, valor_total, data_transacao 
        FROM transacoes 
        WHERE usuario_id = %s AND data_transacao >= %s
        ORDER BY data_transacao ASC LIMIT 1
    """, (user_id, hoje.date()))
    proxima_conta = cursor.fetchone()

    # --- CONSULTA 3: Dados do Gráfico ---
    sql_grafico = """
        SELECT c.nome, SUM(t.valor_total) as total
        FROM transacoes t
        JOIN categorias c ON t.categoria_id = c.id
        WHERE t.usuario_id = %s AND MONTH(t.data_transacao) = %s AND YEAR(t.data_transacao) = %s
        GROUP BY c.nome
    """
    cursor.execute(sql_grafico, (user_id, hoje.month, hoje.year))
    dados_grafico = cursor.fetchall()
    
    # Preparar listas para o JS
    labels = [row['nome'] for row in dados_grafico]
    valores = [float(row['total']) for row in dados_grafico]

    # --- AGORA SIM: Fechar após TODAS as consultas ---
    cursor.close()
    conn.close()
    
    return render_template('index.html', 
                           gasto_mes=gasto_mes, 
                           proxima_conta=proxima_conta,
                           labels=labels, 
                           valores=valores,
                           datetime_now=hoje)

@app.route('/novo_lancamento')
def novo_lancamento():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias ORDER BY nome")
    categorias = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('novo_lancamento.html', categorias=categorias)

@app.route('/salvar', methods=['POST'])
def salvar():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    descricao = request.form.get('descricao')
    valor_total = float(request.form.get('valor'))
    metodo = request.form.get('metodo')
    data_inicial = datetime.strptime(request.form.get('data'), '%Y-%m-%d')
    num_parcelas = int(request.form.get('num_parcelas', 1)) if metodo == 'Cartão de Crédito' else 1

    valor_parcela = valor_total / num_parcelas
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Se for parcelado, criamos várias entradas no banco
        for i in range(num_parcelas):
            # Calcula a data da próxima parcela (adicionando meses)
            data_parcela = data_inicial + timedelta(days=30*i)
            
            sql = """INSERT INTO transacoes 
                     (usuario_id, categoria_id, valor_total, descricao, data_transacao, metodo_pagamento, tipo, is_parcelado, numero_parcelas, parcela_atual) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            
            cat_id = request.form.get('categoria_id')
            user_id = session['usuario_id']
            valores = (user_id, cat_id, valor_parcela, f"{descricao} ({i+1}/{num_parcelas})", data_parcela, metodo, 'despesa', num_parcelas > 1, num_parcelas, i+1)
                        
            cursor.execute(sql, valores)
        
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    except Exception as e:
        return f"Erro ao salvar: {str(e)}"

@app.route('/listagem')
def listagem():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    
    mes = request.args.get('mes', mes_atual, type=int)
    ano = request.args.get('ano', ano_atual, type=int)

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # Usamos LEFT JOIN para garantir que a transação apareça 
        # mesmo que a categoria tenha algum problema
        sql = """
            SELECT t.*, c.nome as categoria_nome 
            FROM transacoes t
            LEFT JOIN categorias c ON t.categoria_id = c.id
            WHERE t.usuario_id = %s 
              AND MONTH(t.data_transacao) = %s 
              AND YEAR(t.data_transacao) = %s
            ORDER BY t.data_transacao ASC
        """
        cursor.execute(sql, (session['usuario_id'], mes, ano))
        dados = cursor.fetchall()
        
        # SQL para a soma (Total do Mês)
        cursor.execute("""
            SELECT SUM(valor_total) as total 
            FROM transacoes 
            WHERE usuario_id = %s 
              AND MONTH(data_transacao) = %s 
              AND YEAR(data_transacao) = %s
        """, (session['usuario_id'], mes, ano))
        
        soma = cursor.fetchone()
        total_gasto = soma['total'] if soma['total'] else 0.0
        
        cursor.close()
        conn.close()
        
        return render_template('listagem.html', 
                               transacoes=dados, 
                               total_gasto=total_gasto, 
                               mes_sel=mes, 
                               ano_sel=ano)
    except Exception as e:
        return f"Erro ao carregar listagem: {str(e)}"

@app.route('/excluir/<int:id>')
def excluir(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Deleta a transação específica pelo ID
        sql = "DELETE FROM transacoes WHERE id = %s"
        cursor.execute(sql, (id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('listagem'))
    except Exception as e:
        return f"Erro ao excluir: {str(e)}"

@app.route('/categorias')
def categorias():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias ORDER BY nome")
    lista_categorias = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('categorias.html', categorias=lista_categorias)

@app.route('/salvar_categoria', methods=['POST'])
def salvar_categoria():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Normalizamos o nome (remove espaços e padroniza maiúsculas)
    nome_cat = request.form.get('nome_categoria').strip().capitalize()
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    try:
        cursor.execute("INSERT INTO categorias (nome) VALUES (%s)", (nome_cat,))
        conn.commit()
    except mysql.connector.Error as err:
        if err.errno == 1062:
            cursor.execute("SELECT * FROM categorias ORDER BY nome")
            todas = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('categorias.html', categorias=todas, erro=f"A categoria '{nome_cat}' já existe!")
    
    cursor.close()
    conn.close()
    return redirect(url_for('categorias'))

    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        # Tenta excluir. Nota: Se houver transações com essa categoria, 
        # o MySQL pode dar erro de Foreign Key dependendo da sua estrutura.
        cursor.execute("DELETE FROM categorias WHERE id = %s", (id,))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Erro ao excluir categoria: {err}")
        # Aqui você poderia tratar se não pode excluir por causa de transações vinculadas
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('categorias'))

@app.route('/editar_categoria/<int:id>')
def editar_categoria(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias WHERE id = %s", (id,))
    categoria = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('editar_categoria.html', categoria=categoria)

@app.route('/atualizar_categoria/<int:id>', methods=['POST'])
def atualizar_categoria(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    novo_nome = request.form.get('nome_categoria').strip().capitalize()
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    try:
        cursor.execute("UPDATE categorias SET nome = %s WHERE id = %s", (novo_nome, id))
        conn.commit()
        return redirect(url_for('categorias'))
    except mysql.connector.Error as err:
        if err.errno == 1062:
            # Se o novo nome for duplicado
            cursor.execute("SELECT * FROM categorias WHERE id = %s", (id,))
            categoria = cursor.fetchone()
            return render_template('editar_categoria.html', categoria=categoria, erro="Já existe uma categoria com este nome!")
    finally:
        cursor.close()
        conn.close()

@app.route('/excluir_categoria/<int:id>', methods=['POST'])
def excluir_categoria(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # 1. Verificar se existem transações usando esta categoria
    cursor.execute("SELECT COUNT(*) as total FROM transacoes WHERE categoria_id = %s", (id,))
    resultado = cursor.fetchone()
    
    if resultado['total'] > 0:
        # EXISTEM TRANSAÇÕES: Não podemos excluir
        cursor.execute("SELECT * FROM categorias ORDER BY nome")
        todas = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('categorias.html', 
                               categorias=todas, 
                               erro="Não é possível excluir: existem transações cadastradas nesta categoria!")

    # 2. Se não houver transações, exclui normalmente
    cursor.execute("DELETE FROM categorias WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('categorias'))

if __name__ == '__main__':
    app.run(debug=True)