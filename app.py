from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from datetime import datetime
from dateutil.relativedelta import relativedelta

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

# Cadastro de usuário
@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')

# Rota para processar o cadastro
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

# Perfil do usuário
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

# Excluir conta do usuário
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

# Login
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

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Página Inicial
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
    
    cursor.execute("SELECT SUM(valor_total) as total FROM transacoes WHERE usuario_id = %s AND pago = FALSE", (user_id,))
    total_pendente = cursor.fetchone()['total'] or 0.0

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

# Novo Lançamento
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

# Salvar Lançamento
@app.route('/salvar', methods=['POST'])
def salvar():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    user_id = session['usuario_id']
    
    # 1. Capturar todos os campos do formulário
    descricao_base = request.form.get('descricao', '').strip()
    valor_total = float(request.form.get('valor', 0))
    data_str = request.form.get('data')
    categoria_id = request.form.get('categoria')
    metodo = request.form.get('metodo') # Captura o método selecionado
    parcelas = int(request.form.get('parcelas', 1)) # Captura a qtde de parcelas
    
    # Checkbox de pagamento
    pago_form = 1 if request.form.get('pago') else 0

    if not categoria_id or not valor_total or not data_str:
        return "Erro: Categoria, Valor e Data são obrigatórios.", 400

    # 2. Calcular o valor de cada parcela
    valor_parcela = round(valor_total / parcelas, 2)

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        data_atual = datetime.strptime(data_str, '%Y-%m-%d')
        
        # 3. Loop para inserir cada parcela como uma linha no banco
        for i in range(parcelas):
            # Adiciona (1/3), (2/3) na descrição se for parcelado
            desc_final = f"{descricao_base} ({i+1}/{parcelas})" if parcelas > 1 else descricao_base
            
            # Regra: Apenas a primeira parcela pode ser 'paga' agora. 
            # As futuras (i > 0) sempre começam como pendentes.
            status_pago = pago_form if i == 0 else 0

            sql = """
                INSERT INTO transacoes 
                (usuario_id, categoria_id, descricao, valor_total, data_transacao, metodo_pagamento, pago) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            valores = (user_id, categoria_id, desc_final, valor_parcela, 
                       data_atual.strftime('%Y-%m-%d'), metodo, status_pago)
            
            cursor.execute(sql, valores)
            
            # Avança a data em 1 mês para a próxima parcela
            data_atual += relativedelta(months=1)
            
        conn.commit()
        
    except Exception as e:
        print(f"Erro ao salvar: {e}")
        return f"Erro interno: {e}", 500
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('listagem'))
    # 1. Verificar sessão
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    user_id = session['usuario_id']
    
    # 2. Capturar e tratar os dados
    descricao = request.form.get('descricao', '').strip()
    valor = request.form.get('valor')
    data = request.form.get('data')
    categoria_id = request.form.get('categoria')
    
    # Checkbox: se vier 'on' vira 1, senão 0
    pago = 1 if request.form.get('pago') else 0

    # 3. Validação rigorosa para evitar erro de banco (Column cannot be null)
    if not categoria_id or not valor or not data:
        return "Erro: Categoria, Valor e Data são obrigatórios.", 400

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        # 4. Inserir no banco
        sql = """
            INSERT INTO transacoes (usuario_id, categoria_id, descricao, valor_total, data_transacao, pago) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        # Convertemos o valor para float aqui dentro do try para capturar erros de digitação
        valores = (user_id, categoria_id, descricao, float(valor), data, pago)
        
        cursor.execute(sql, valores)
        conn.commit()
        
    except Exception as e:
        print(f"Erro ao salvar: {e}")
        return f"Erro interno: {e}", 500
    finally:
        # 5. Garantir que a conexão sempre feche
        cursor.close()
        conn.close()
    
    return redirect(url_for('listagem'))

# Listagem de Lançamentos
@app.route('/listagem')
def listagem():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['usuario_id']
    busca = request.args.get('busca', '')
    mes_filtro = request.args.get('mes_filtro', '') 

    # --- LÓGICA DO MÊS VIGENTE ---
    # Se o usuário não escolheu um mês no filtro, definimos o mês atual como padrão
    if not mes_filtro and not busca:
        mes_filtro = datetime.now().strftime('%Y-%m')
    # -----------------------------

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT t.*, c.nome as categoria_nome 
        FROM transacoes t 
        JOIN categorias c ON t.categoria_id = c.id 
        WHERE t.usuario_id = %s
    """
    params = [user_id]

    if busca:
        sql += " AND t.descricao LIKE %s"
        params.append(f"%{busca}%")

    if mes_filtro:
        ano, mes = mes_filtro.split('-')
        sql += " AND YEAR(t.data_transacao) = %s AND MONTH(t.data_transacao) = %s"
        params.extend([ano, mes])

    sql += " ORDER BY t.data_transacao DESC"
    
    cursor.execute(sql, tuple(params))
    lista = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Passamos o mes_filtro de volta para o HTML para o campo 'month' ficar preenchido
    return render_template('listagem.html', transacoes=lista, mes_atual=mes_filtro)

# Excluir Lançamento
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

# Gestão de Categorias
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

# Salvar Categoria
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

# Editar Categoria
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

# Atualizar Categoria
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

# Excluir Categoria
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

# Editar Lançamento
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_transacao(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['usuario_id']
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Captura os novos dados do formulário
        descricao = request.form.get('descricao')
        valor = request.form.get('valor')
        data = request.form.get('data')
        categoria_id = request.form.get('categoria')
        metodo = request.form.get('metodo') # Verifique se você tem esta coluna no banco
        pago = 1 if request.form.get('pago') else 0

        sql = """
            UPDATE transacoes 
            SET descricao=%s, valor_total=%s, data_transacao=%s, categoria_id=%s, metodo_pagamento=%s, pago=%s
            WHERE id=%s AND usuario_id=%s
        """
        cursor.execute(sql, (descricao, valor, data, categoria_id, metodo, pago, id, user_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        return redirect(url_for('listagem'))

    # Se for GET: Busca os dados atuais da transação
    cursor.execute("SELECT * FROM transacoes WHERE id = %s AND usuario_id = %s", (id, user_id))
    transacao = cursor.fetchone()

    # Busca as categorias para o dropdown
    cursor.execute("SELECT * FROM categorias")
    categorias = cursor.fetchall()

    cursor.close()
    conn.close()

    if not transacao:
        return "Transação não encontrada", 404

    return render_template('editar_transacao.html', t=transacao, categorias=categorias)

# Alternar Status de Pagamento
@app.route('/alternar_pagamento/<int:id>')
def alternar_pagamento(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['usuario_id']
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        # O SQL 'pago = NOT pago' inverte 0 para 1 e 1 para 0 automaticamente
        sql = "UPDATE transacoes SET pago = NOT pago WHERE id = %s AND usuario_id = %s"
        cursor.execute(sql, (id, user_id))
        conn.commit()
    except Exception as e:
        print(f"Erro ao alterar status: {e}")
    finally:
        cursor.close()
        conn.close()
    
    # Redireciona de volta para a listagem mantendo os filtros de busca/mês se existirem
    return redirect(request.referrer or url_for('listagem'))


















if __name__ == '__main__':
    app.run(debug=True)