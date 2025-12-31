from flask import Flask, flash, jsonify, render_template, request, redirect, url_for, session
import mysql.connector
from datetime import datetime
from dateutil.relativedelta import relativedelta
from werkzeug.security import generate_password_hash, check_password_hash

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
    'host': '127.0.0.1',  # Use o IP em vez de 'localhost' para evitar conflitos no Windows
    'user': 'root',
    'password': 'Dc524876_*',
    'database': 'controle_financeiro',
    'auth_plugin': 'mysql_native_password'
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
    senha_criptografada = generate_password_hash(request.form.get('senha'))    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Insere o novo usuário
        sql = "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)"
        cursor.execute(sql, (nome, email, senha_criptografada))
        
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
        
        # Se o usuário digitou uma nova senha
        if nova_senha and nova_senha.strip() != "":
            senha_hash = generate_password_hash(nova_senha)
            sql = "UPDATE usuarios SET nome = %s, email = %s, senha = %s WHERE id = %s"
            params = (novo_nome, novo_email, senha_hash, session['usuario_id'])
        else:
            # Se não digitou senha, atualiza apenas nome e email
            sql = "UPDATE usuarios SET nome = %s, email = %s WHERE id = %s"
            params = (novo_nome, novo_email, session['usuario_id'])
        
        cursor.execute(sql, params)
        conn.commit()
        
        # Atualiza a sessão para o nome mudar no menu imediatamente
        session['usuario_nome'] = novo_nome
        flash("Perfil atualizado com sucesso!", "sucesso")
        return redirect(url_for('perfil')) # Redireciona para limpar o POST
    
    # Busca os dados atuais (não precisamos mais da senha aqui)
    cursor.execute("SELECT nome, email FROM usuarios WHERE id = %s", (session['usuario_id'],))
    usuario = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('perfil.html', usuario=usuario)

# Excluir conta do usuário
@app.route('/excluir_conta', methods=['POST'])
def excluir_conta():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['usuario_id']
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 1. Deletar todas as transações (inclusive parceladas) vinculadas ao usuário
        cursor.execute("DELETE FROM transacoes WHERE usuario_id = %s", (user_id,))
        
        # 2. Deletar categorias personalizadas (se o seu sistema tiver essa tabela)
        # cursor.execute("DELETE FROM categorias WHERE usuario_id = %s", (user_id,))
        
        # 3. Por fim, deletar o usuário
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (user_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Limpa a sessão para que o usuário seja deslogado imediatamente
        session.clear()
        
        flash("Sua conta e todos os seus dados foram excluídos com sucesso.", "sucesso")
        return redirect(url_for('login'))
        
        # Redireciona para o login com uma "falsa" confirmação (opcional)
        return redirect(url_for('login'))
        
    except Exception as e:
        if conn:
            conn.rollback() # Cancela tudo se der erro no meio do caminho
        flash(f"Erro ao excluir conta: {str(e)}", "erro")
        return redirect(url_for('perfil'))
    
# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if usuario and check_password_hash(usuario['senha'], senha):
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome'] # Adicione esta linha!
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
    
    # 1. PEGA O MÊS E ANO DA URL (Navegação)
    mes_atual = int(request.args.get('mes', hoje.month))
    ano_atual = int(request.args.get('ano', hoje.year))
    data_foco = datetime(ano_atual, mes_atual, 1)
    
    # Datas para os botões de navegação
    data_anterior = data_foco - relativedelta(months=1)
    data_proxima = data_foco + relativedelta(months=1)

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # PARÂMETROS ÚNICOS PARA TODAS AS CONSULTAS DO MÊS SELECIONADO
    params_mes = (user_id, mes_atual, ano_atual)
    sql_base_mes = "FROM transacoes WHERE usuario_id = %s AND MONTH(data_transacao) = %s AND YEAR(data_transacao) = %s"

    # --- 2. CONSULTAS DOS CARDS (Azul, Verde, Laranja) ---
    cursor.execute(f"SELECT SUM(valor_total) as total {sql_base_mes}", params_mes)
    res_gasto = cursor.fetchone()['total']
    gasto_mes = float(res_gasto) if res_gasto else 0.0

    cursor.execute(f"SELECT SUM(valor_total) as total {sql_base_mes} AND pago = 1", params_mes)
    res_pago = cursor.fetchone()['total']
    total_pago = float(res_pago) if res_pago else 0.0

    cursor.execute(f"SELECT SUM(valor_total) as total {sql_base_mes} AND pago = 0", params_mes)
    res_pendente = cursor.fetchone()['total']
    total_pendente = float(res_pendente) if res_pendente else 0.0

    # --- 3. DADOS DO GRÁFICO POR CATEGORIA (Sincronizado) ---
    cursor.execute(f"""
        SELECT c.nome, SUM(t.valor_total) as total
        FROM transacoes t
        JOIN categorias c ON t.categoria_id = c.id
        WHERE t.usuario_id = %s AND MONTH(t.data_transacao) = %s AND YEAR(t.data_transacao) = %s
        GROUP BY c.nome
    """, params_mes)
    dados_grafico = cursor.fetchall()
    labels = [row['nome'] for row in dados_grafico]
    valores = [float(row['total']) for row in dados_grafico]

    # --- 4. RESUMO POR MÉTODO DE PAGAMENTO (Sincronizado) ---
    cursor.execute("""
    SELECT metodo_pagamento, SUM(valor_total) as total 
    FROM transacoes 
    WHERE usuario_id = %s AND MONTH(data_transacao) = %s AND YEAR(data_transacao) = %s
    GROUP BY metodo_pagamento
""", (user_id, mes_atual, ano_atual))
    resumo_metodos = cursor.fetchall()

    labels_metodos = [row['metodo_pagamento'] for row in resumo_metodos]
    valores_metodos = [float(row['total']) for row in resumo_metodos]
    # --- 5. PRÓXIMAS CONTAS (Geral - Pendentes) ---
    cursor.execute("""
        SELECT id, descricao, valor_total, data_transacao 
        FROM transacoes 
        WHERE usuario_id = %s AND pago = 0 
        ORDER BY data_transacao ASC
    """, (user_id,))
    proximas_contas = cursor.fetchall()

    # --- 6. TOTAL ATRASADAS (Comparado a Hoje real, não ao mês navegado) ---
    cursor.execute("""
        SELECT COUNT(*) as total FROM transacoes 
        WHERE usuario_id = %s AND pago = 0 AND data_transacao < %s
    """, (user_id, hoje.date()))
    total_atrasadas = cursor.fetchone()['total']

    cursor.close()
    conn.close()
    
    return render_template('index.html', 
                           gasto_mes=gasto_mes, total_pago=total_pago, total_pendente=total_pendente,
                           labels=labels, valores=valores,
                           labels_metodos=labels_metodos, valores_metodos=valores_metodos,
                           proximas_contas=proximas_contas, total_atrasadas=total_atrasadas,
                           datetime_now=data_foco, data_anterior=data_anterior, data_proxima=data_proxima)

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
    
    # PEGA A DATA DE HOJE NO FORMATO YYYY-MM-DD
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    # PASSA A VARIÁVEL 'hoje' PARA O HTML
    return render_template('novo_lancamento.html', categorias=categorias, hoje=hoje)
   
# Salvar Lançamento
@app.route('/salvar', methods=['POST'])
def salvar():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    user_id = session['usuario_id']
    
    # 1. Capturar dados do formulário
    descricao_base = request.form.get('descricao', 'Sem descrição').strip()
    valor_total = float(request.form.get('valor_total', 0))
    data_str = request.form.get('data_transacao')
    categoria_id = request.form.get('categoria_id')
    metodo = request.form.get('metodo')
    pago_form = 1 if request.form.get('pago') else 0
    
    # Lógica de Parcelas
    num_parcelas = int(request.form.get('numero_parcelas', 1)) if metodo == "Cartão de Crédito" else 1

    # 2. Cálculos de precisão (centavos)
    valor_parcela = round(valor_total / num_parcelas, 2)
    sobra_centavos = round(valor_total - (valor_parcela * num_parcelas), 2)

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    id_pai = None

    try:
        data_atual = datetime.strptime(data_str, '%Y-%m-%d')
        
        for i in range(1, num_parcelas + 1):
            desc_final = f"{descricao_base} ({i}/{num_parcelas})" if num_parcelas > 1 else descricao_base
            status_pago = pago_form if i == 1 else 0
            valor_final_da_parcela = valor_parcela + (sobra_centavos if i == num_parcelas else 0)

            sql = """
                INSERT INTO transacoes 
                (usuario_id, categoria_id, descricao, valor_total, data_transacao, 
                 metodo_pagamento, pago, is_parcelado, numero_parcelas, parcela_atual, id_transacao_pai) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            valores = (user_id, categoria_id, desc_final, valor_final_da_parcela, 
                       data_atual.strftime('%Y-%m-%d'), metodo, status_pago,
                       1 if num_parcelas > 1 else 0, num_parcelas, i, id_pai)
            
            cursor.execute(sql, valores)
            
            if i == 1:
                conn.commit()
                id_pai = cursor.lastrowid
            
            data_atual += relativedelta(months=1)
            
        conn.commit()
        flash(f"Sucesso! Lançamento de '{descricao_base}' adicionado.", "sucesso")
        
        # MENSAGEM DE SUCESSO
        if num_parcelas > 1:
            flash(f"Lançamento parcelado ({num_parcelas}x) criado com sucesso!", "sucesso")
        else:
            flash("Lançamento simples criado com sucesso!", "sucesso")

    except Exception as e:
        conn.rollback()
        flash(f"Erro ao salvar lançamento: {str(e)}", "erro")
        return redirect(url_for('novo_lancamento'))
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('novo_lancamento'))

# Listagem de Lançamentos
@app.route('/listagem')
def listagem():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['usuario_id']
    filtro = request.args.get('filtro')
    hoje = datetime.now().date()
    
    # 1. Captura dos filtros
    busca = request.args.get('busca', '')
    mes_filtro = request.args.get('mes_filtro', '')
    ano_filtro = request.args.get('ano_filtro', '')
    metodo_filtro = request.args.get('metodo', '')
    status_filtro = request.args.get('status', '')

    # Lógica de prioridade: Se escolheu Ano Todo, ele manda no período
    periodo = ""
    if ano_filtro:
        periodo = ano_filtro
    elif mes_filtro:
        periodo = mes_filtro
    elif not busca:
        # Padrão: Mês atual se não houver busca
        periodo = datetime.now().strftime('%Y-%m')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # 2. Construção da Query Base (Uma única vez!)
    query_base = " FROM transacoes t JOIN categorias c ON t.categoria_id = c.id WHERE t.usuario_id = %s"
    params = [user_id]

    # Filtro de Data (Ano ou Mês)
    if periodo:
        if len(periodo) == 7: # Formato YYYY-MM
            ano, mes = periodo.split('-')
            query_base += " AND YEAR(t.data_transacao) = %s AND MONTH(t.data_transacao) = %s"
            params.extend([ano, mes])
        elif len(periodo) == 4: # Formato YYYY
            query_base += " AND YEAR(t.data_transacao) = %s"
            params.append(periodo)

    # Filtro de Busca
    if busca:
        query_base += " AND t.descricao LIKE %s"
        params.append(f"%{busca}%")

    # Filtro de Método
    if metodo_filtro:
        query_base += " AND t.metodo_pagamento = %s"
        params.append(metodo_filtro)

    # Filtro de Status
    if status_filtro != '' and status_filtro is not None:
        query_base += " AND t.pago = %s"
        params.append(status_filtro)
    
    if filtro == 'atrasadas':
        # Busca apenas contas NÃO pagas de datas ANTERIORES a hoje
        query = """
            SELECT t.*, c.nome as categoria_nome 
            FROM transacoes t
            JOIN categorias c ON t.categoria_id = c.id
            WHERE t.usuario_id = %s AND t.pago = 0 AND t.data_transacao < %s
            ORDER BY t.data_transacao ASC
        """
        cursor.execute(query, (user_id, hoje))
        titulo_pagina = "Contas Pendentes (Atrasadas)"
    else:
        # Busca padrão (todas do mês atual ou geral, conforme sua lógica atual)
        query = """
            SELECT t.*, c.nome as categoria_nome 
            FROM transacoes t
            JOIN categorias c ON t.categoria_id = c.id
            WHERE t.usuario_id = %s
            ORDER BY t.data_transacao DESC
        """
        cursor.execute(query, (user_id,))
        titulo_pagina = "Extrato de Transações"
    
    transacoes = cursor.fetchall()
    # 3. Execução das Consultas
    # Lista Principal
    sql_lista = "SELECT t.*, c.nome as categoria_nome " + query_base + " ORDER BY t.data_transacao DESC"
    cursor.execute(sql_lista, tuple(params))
    lista = cursor.fetchall()

    # Total Pago
    cursor.execute("SELECT SUM(t.valor_total) as total " + query_base + " AND t.pago = 1", tuple(params))
    res_pago = cursor.fetchone()['total']
    total_pago = float(res_pago) if res_pago else 0.0

    # Total Pendente
    cursor.execute("SELECT SUM(t.valor_total) as total " + query_base + " AND t.pago = 0", tuple(params))
    res_pendente = cursor.fetchone()['total']
    total_pendente = float(res_pendente) if res_pendente else 0.0

    total_geral = total_pago + total_pendente

    cursor.close()
    conn.close()
    
    return render_template('listagem.html', 
                           transacoes=transacoes,
                           titulo=titulo_pagina,
                           mes_atual=mes_filtro, 
                           total_pago=total_pago, 
                           total_pendente=total_pendente,
                           total_geral=total_geral)
    
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

# ROTA PARA ABRIR A TELA DE EDIÇÃO
@app.route('/editar/<int:id>', methods=['GET'])
def editar(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # Busca a transação específica
    cursor.execute("SELECT * FROM transacoes WHERE id = %s AND usuario_id = %s", (id, session['usuario_id']))
    transacao = cursor.fetchone()
    
    # Busca categorias para o select
    cursor.execute("SELECT * FROM categorias ORDER BY nome")
    categorias = cursor.fetchall()
    
    cursor.close()
    conn.close()

    if not transacao:
        return "Transação não encontrada", 404

    # Enviamos como 'transacao' para o HTML
    return render_template('editar_transacao.html', transacao=transacao, categorias=categorias)

# ROTA PARA PROCESSAR A ATUALIZAÇÃO (POST)
@app.route('/atualizar/<int:id>', methods=['POST'])
def atualizar(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    # 1. Capturar dados do formulário (Sincronizado com seu HTML)
    nova_descricao = request.form.get('descricao')
    novo_valor = float(request.form.get('valor_total', 0))
    nova_data = request.form.get('data_transacao')
    nova_categoria = request.form.get('categoria_id')
    novo_metodo = request.form.get('metodo')
    pago = 1 if request.form.get('pago') else 0
    tipo_edicao = request.form.get('tipo_edicao', 'individual')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    try:
        # Busca dados originais para checar parcelamento
        cursor.execute("SELECT id_transacao_pai, is_parcelado FROM transacoes WHERE id = %s", (id,))
        original = cursor.fetchone()

        if tipo_edicao == 'grupo' and (original['id_transacao_pai'] or original['is_parcelado']):
                    id_pai = original['id_transacao_pai'] if original['id_transacao_pai'] else id
                    nome_limpo = nova_descricao.split(' (')[0].strip()
                    
                    # Novo total vindo do formulário
                    novo_total = int(request.form.get('novo_total_parcelas', original['numero_parcelas']))
                    antigo_total = original['numero_parcelas']

                    # 1. Atualiza as parcelas que JÁ EXISTEM (Nome e Novo Total)
                    sql_update_existentes = """
                        UPDATE transacoes 
                        SET descricao = CONCAT(%s, ' (', parcela_atual, '/', %s, ')'),
                            categoria_id = %s,
                            metodo_pagamento = %s,
                            numero_parcelas = %s
                        WHERE id = %s OR id_transacao_pai = %s
                    """
                    cursor.execute(sql_update_existentes, (nome_limpo, novo_total, nova_categoria, novo_metodo, novo_total, id_pai, id_pai))

                    # 2. Se o novo total for MAIOR, cria as parcelas que faltam
                    if novo_total > antigo_total:
                        # Busca a data e valor da última parcela existente para servir de base
                        cursor.execute("SELECT data_transacao, valor_total FROM transacoes WHERE id_transacao_pai = %s OR id = %s ORDER BY parcela_atual DESC LIMIT 1", (id_pai, id_pai))
                        ultima_parcela = cursor.fetchone()
                        
                        base_date = ultima_parcela['data_transacao']
                        valor_cada = ultima_parcela['valor_total']

                        for i in range(antigo_total + 1, novo_total + 1):
                            nova_data = base_date + relativedelta(months=(i - antigo_total))
                            desc_nova = f"{nome_limpo} ({i}/{novo_total})"
                            
                            sql_insere_novas = """
                                INSERT INTO transacoes 
                                (usuario_id, categoria_id, descricao, valor_total, data_transacao, 
                                metodo_pagamento, pago, is_parcelado, numero_parcelas, parcela_atual, id_transacao_pai) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            valores = (session['usuario_id'], nova_categoria, desc_nova, valor_cada, 
                                    nova_data, novo_metodo, 0, 1, novo_total, i, id_pai)
                            cursor.execute(sql_insere_novas, valores)
                    # --- ATUALIZAÇÃO EM GRUPO ---
                    id_pai = original['id_transacao_pai'] if original['id_transacao_pai'] else id
                    nome_limpo = nova_descricao.split(' (')[0].strip()

                    sql_grupo = """
                        UPDATE transacoes 
                        SET descricao = CONCAT(%s, ' (', parcela_atual, '/', numero_parcelas, ')'),
                            categoria_id = %s,
                            metodo_pagamento = %s
                        WHERE id = %s OR id_transacao_pai = %s
                    """
                    cursor.execute(sql_grupo, (nome_limpo, nova_categoria, novo_metodo, id_pai, id_pai))
        else:
            # --- ATUALIZAÇÃO INDIVIDUAL ---
            sql_individual = """
                UPDATE transacoes 
                SET descricao = %s, valor_total = %s, data_transacao = %s, 
                    categoria_id = %s, metodo_pagamento = %s, pago = %s
                WHERE id = %s
            """
            cursor.execute(sql_individual, (nova_descricao, novo_valor, nova_data, 
                                           nova_categoria, novo_metodo, pago, id))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao atualizar: {e}")
        return f"Erro: {e}", 500
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('listagem'))

# Alternar Status de Pagamento
@app.route('/alternar_pagamento/<int:id>', methods=['POST'])
def alternar_pagamento(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # Busca o status atual para inverter (se era 0 vira 1, se era 1 vira 0)
    cursor.execute("SELECT pago FROM transacoes WHERE id = %s", (id,))
    resultado = cursor.fetchone()
    
    if resultado:
        novo_status = 0 if resultado[0] == 1 else 1
        cursor.execute("UPDATE transacoes SET pago = %s WHERE id = %s", (novo_status, id))
        conn.commit()
        
        if novo_status == 1:
            flash("Conta marcada como paga!", "sucesso")
        else:
            flash("Conta marcada como pendente!", "sucesso")

    # Recalcula os totais (Exemplo para o mês atual)
    cursor.execute("""
        SELECT 
            SUM(valor_total) as total,
            SUM(CASE WHEN pago = 1 THEN valor_total ELSE 0 END) as pago,
            SUM(CASE WHEN pago = 0 THEN valor_total ELSE 0 END) as pendente
        FROM transacoes 
        WHERE usuario_id = %s AND MONTH(data_transacao) = MONTH(CURRENT_DATE())
    """, (session['usuario_id'],))
    res = cursor.fetchone()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'status': 'sucesso',
            'novo_total': float(res[0] or 0),
            'novo_pago': float(res[1] or 0),
            'novo_pendente': float(res[2] or 0)
        })


    cursor.close()
    conn.close()
    
    # Redireciona de volta para a index para atualizar o carrossel e o gráfico
    return redirect(request.referrer or url_for('index'))

@app.route('/quitar_proxima/<int:id>')
def quitar_proxima(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("UPDATE transacoes SET pago = 1 WHERE id = %s AND usuario_id = %s", 
                   (id, session['usuario_id']))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # Atualiza a transação para paga
    cursor.execute("UPDATE transacoes SET pago = 1 WHERE id = %s AND usuario_id = %s", 
                   (id, session['usuario_id']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Conta marcada como paga com sucesso!', 'success')
    return redirect(url_for('index'))
















if __name__ == '__main__':
    app.run(debug=True)