from flask import Flask, flash, jsonify, render_template, request, redirect, url_for, session, send_file
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from werkzeug.security import generate_password_hash, check_password_hash
import io
import mysql.connector
import pandas as pd
import random
import locale
import calendar
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
except:
    locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')

app = Flask(__name__)
app.secret_key = 'uma_chave_muito_segura_aqui'

@app.context_processor
def inject_now():
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    agora = datetime.now()
    return {
        'datetime_now': agora,
        'mes_atual_pt': meses_pt[agora.month],
        'meses_mapa': meses_pt
    }
    
# CONFIGURAÇÃO DO SEU BANCO (Ajuste a senha!)
db_config = {
    'host': '127.0.0.1',  # Use o IP em vez de 'localhost' para evitar conflitos no Windows
    'user': 'root',
    'password': 'Dc524876_*',
    'database': 'controle_financeiro',
    'auth_plugin': 'mysql_native_password'
}

def obter_nome_mes(numero_mes):
    meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    return meses.get(int(numero_mes), "Mes")

@app.template_filter('moeda')
def moeda_filter(valor):
    if valor is None:
        return "R$ 0,00"
    try:
        return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "R$ 0,00"

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
    
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 1. Insere o novo usuário
        sql_user = "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)"
        cursor.execute(sql_user, (nome, email, senha_criptografada))
        
        # 2. Pega o ID do usuário que acabou de ser criado
        novo_usuario_id = cursor.lastrowid
        
        # 3. Define as categorias padrão do sistema
        # Formato: (nome, cor, tipo, usuario_id, is_sistema)
        categorias_padrao = [
            ('Alimentação', '#e74c3c', 'despesa', novo_usuario_id, True),
            ('Moradia', '#3498db', 'despesa', novo_usuario_id, True),
            ('Transporte', '#f1c40f', 'despesa', novo_usuario_id, True),
            ('Lazer', '#2ecc71', 'despesa', novo_usuario_id, True),
            ('Saúde', '#9b59b6', 'despesa', novo_usuario_id, True),
            ('Salário', '#27ae60', 'receita', novo_usuario_id, True),
            ('Investimentos', '#bc1a93', 'investimento', novo_usuario_id, True)
        ]
        
        # 4. Insere as categorias em massa
        sql_cat = "INSERT INTO categorias (nome, cor, tipo, usuario_id, is_sistema) VALUES (%s, %s, %s, %s, %s)"
        cursor.executemany(sql_cat, categorias_padrao)
        
        conn.commit()
        flash("Conta criada com sucesso! Agora você já pode entrar.", "sucesso")
        return redirect(url_for('login'))

    except Exception as e:
        if conn:
            conn.rollback()
        return f"Erro ao cadastrar: {str(e)}"
    finally:
        if conn:
            cursor.close()
            conn.close()
            
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
        
        # 1. Deleta transações
        cursor.execute("DELETE FROM transacoes WHERE usuario_id = %s", (user_id,))
        
        # 2. NOVO: Deleta categorias (incluindo as de sistema do usuário)
        cursor.execute("DELETE FROM categorias WHERE usuario_id = %s", (user_id,))
        
        # 3. Deleta usuário
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (user_id,))
        
        conn.commit()
        session.clear()
        flash("Sua conta e todos os seus dados foram apagados.", "sucesso")
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
    
    mes_atual = int(request.args.get('mes', hoje.month))
    ano_atual = int(request.args.get('ano', hoje.year))
    data_foco = datetime(ano_atual, mes_atual, 1)
    
    meses_mapa = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    mes_selecionado_pt = meses_mapa[mes_atual]
    
    data_anterior = data_foco - relativedelta(months=1)
    data_proxima = data_foco + relativedelta(months=1)

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    try:
        # Busca todas as transações do mês para calcular no Python (Garante precisão)
        query_lista = """
            SELECT * FROM transacoes 
            WHERE usuario_id = %s AND MONTH(data_transacao) = %s AND YEAR(data_transacao) = %s
        """
        params = (user_id, mes_atual, ano_atual)
        cursor.execute(query_lista, params)
        transacoes = cursor.fetchall()

        # --- LÓGICA MATEMÁTICA UNIFICADA ---
        
        # 1. Entradas (Tudo que é Receita)
        total_receitas = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'receita')

        # 2. Investimentos (Aporte Mensal)
        total_investimentos = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'investimento' and t['pago'] == 1)

        # 3. Gastos Reais (Apenas o que é Despesa)
        total_despesas_reais = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'despesa')

        # 4. Saldo Projetado (O que sobra: Receita - Despesa - Investimento)
        saldo_projetado = total_receitas - total_despesas_reais - total_investimentos

        # 5. Total Pago (Apenas das Despesas Reais)
        total_pago = sum(float(t['valor_total']) for t in transacoes if t['pago'] == 1 and t['tipo'].strip().lower() == 'despesa')

        # 6. Aguardando Pagamento (Apenas das Despesas Reais)
        total_pendente = sum(float(t['valor_total']) for t in transacoes if t['pago'] == 0 and t['tipo'].strip().lower() == 'despesa')

        # 7. Taxa de Investimento (Para a barra de progresso)
        taxa_invest = (total_investimentos / total_receitas * 100) if total_receitas > 0 else 0

        # --- STATUS E DIAGNÓSTICO ---
        taxa_investimento = (total_investimentos / total_receitas * 100) if total_receitas > 0 else 0
        
        if saldo_projetado < 0:
            status_financeiro, classe_alerta, sugestao = "Crítico", "text-danger", "Despesas superam receitas!"
        else:
            status_financeiro, classe_alerta, sugestao = "Saudável", "text-success", "Saldo positivo!"

        # --- GRÁFICO POR CATEGORIA ---
        cursor.execute("""
            SELECT c.nome, SUM(t.valor_total) as total, c.cor
            FROM transacoes t
            JOIN categorias c ON t.categoria_id = c.id
            WHERE t.usuario_id = %s AND MONTH(t.data_transacao) = %s AND YEAR(t.data_transacao) = %s
            AND t.tipo = 'despesa' GROUP BY c.id HAVING total > 0
        """, params)
        dados_grafico = cursor.fetchall()
        labels = [d['nome'] for d in dados_grafico]
        valores = [float(d['total']) for d in dados_grafico]
        cores = [d['cor'] for d in dados_grafico]

        # --- CÁLCULOS PARA A LISTA "POR PAGAMENTO" ---

        # Criamos um dicionário para somar valores por método
        pagamentos_map = {}

        # Filtramos apenas Saídas (Despesa e Investimento) para o resumo de pagamentos
        for t in transacoes:
            tipo = t['tipo'].strip().lower()
            esta_pago = t['pago'] == 1 # Verifica se o status é pago
            
            if tipo in ['despesa', 'investimento'] and esta_pago:
                metodo = t['metodo'] if t['metodo'] else 'Não informado'
                valor = float(t['valor_total'])
                
                if metodo in pagamentos_map:
                    pagamentos_map[metodo] += valor
                else:
                    pagamentos_map[metodo] = valor

        # Transformamos o dicionário em duas listas para o HTML/JS
        pagamentos_ordenados = sorted(pagamentos_map.items(), key=lambda item: item[1], reverse=True)
        labels_metodos = list(pagamentos_map.keys())
        valores_metodos = list(pagamentos_map.values())

        # --- PRÓXIMAS CONTAS E ATRASADAS ---
        cursor.execute("""
            SELECT id, descricao, valor_total, data_transacao 
            FROM transacoes 
            WHERE usuario_id = %s AND pago = 0 AND tipo IN ('despesa', 'investimento') 
            ORDER BY data_transacao ASC LIMIT 5
        """, (user_id,))
        proximas_contas = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM transacoes 
            WHERE usuario_id = %s AND pago = 0 AND data_transacao < %s AND tipo IN ('despesa', 'investimento')
        """, (user_id, hoje.date()))
        total_atrasadas = cursor.fetchone()['total']

        # --- COMPARATIVO ANUAL ---
        cursor.execute("""
            SELECT MONTH(data_transacao) as mes,
            SUM(CASE WHEN tipo = 'receita' THEN valor_total ELSE 0 END) as rec,
            SUM(CASE WHEN tipo = 'despesa' THEN valor_total ELSE 0 END) as des,
            SUM(CASE WHEN tipo = 'investimento' THEN valor_total ELSE 0 END) as inv
            FROM transacoes WHERE usuario_id = %s AND YEAR(data_transacao) = %s
            GROUP BY MONTH(data_transacao) ORDER BY MONTH(data_transacao)
        """, (user_id, ano_atual))
        res_anual = cursor.fetchall()
        receitas_anuais, despesas_anuais, investimentos_anuais = [0.0]*12, [0.0]*12, [0.0]*12
        for row in res_anual:
            idx = int(row['mes']) - 1
            receitas_anuais[idx] = float(row['rec'])
            despesas_anuais[idx] = float(row['des'])
            investimentos_anuais[idx] = float(row['inv'])

    finally:
        cursor.close()
        conn.close()

    return render_template('index.html', 
        total_receitas=total_receitas,
        total_geral=total_despesas_reais,
        saldo_atual=saldo_projetado,
        total_pago=total_pago,
        total_pendente=total_pendente,
        total_investimentos=total_investimentos,
        taxa_investimento=taxa_invest,
        status_financeiro=status_financeiro,
        classe_alerta=classe_alerta,
        sugestao=sugestao,
        labels=labels,
        valores=valores,
        cores=cores,
        proximas_contas=proximas_contas,
        total_atrasadas=total_atrasadas,
        receitas_anuais=receitas_anuais,
        despesas_anuais=despesas_anuais,
        investimentos_anuais=investimentos_anuais,
        datetime_now=data_foco,
        mes_atual_pt=mes_selecionado_pt,
        data_anterior=data_anterior,
        data_proxima=data_proxima,
        labels_metodos=labels_metodos,
        valores_metodos=valores_metodos)
    
# Novo Lançamento
@app.route('/novo_lancamento', methods=['GET', 'POST'])
def novo_lancamento():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        descricao = request.form.get('descricao')
        valor_bruto = request.form.get('valor_total') 
        categoria_id = request.form.get('categoria_id')
        data_transacao = request.form.get('data_transacao')
        tipo = request.form.get('tipo')
        metodo = request.form.get('metodo') or 'Dinheiro' # Agora a coluna existe!
        pago = 0 # Define como Pendente por padrão conforme solicitado

        try:
            valor_final = float(valor_bruto)
        except (ValueError, TypeError):
            valor_final = 0.0
            
        sql = """INSERT INTO transacoes (usuario_id, descricao, valor_total, tipo, categoria_id, data_transacao, pago, metodo) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        
        try:
            cursor.execute(sql, (session['usuario_id'], descricao, valor_final, tipo, categoria_id, data_transacao, pago, metodo))
            conn.commit()
        except Exception as e:
            print(f"ERRO AO GRAVAR: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
            
        return redirect(url_for('novo_lancamento'))

    # Restante do código (GET) permanece igual...
    cursor.execute("SELECT * FROM categorias ORDER BY nome")
    categorias = cursor.fetchall()
    cursor.close()
    conn.close()
    from datetime import datetime
    hoje = datetime.now().strftime('%Y-%m-%d')
    return render_template('novo_lancamento.html', categorias=categorias, hoje=hoje)

# Listagem de Lançamentos
@app.route('/listagem')
def listagem():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['usuario_id']
    agora = datetime.now()
    hoje = agora.date()
    
    # Filtros via URL
    busca = request.args.get('busca', '')
    mes_filtro = request.args.get('mes_filtro', agora.strftime('%Y-%m'))
    metodo_filtro = request.args.get('metodo', '')
    status_filtro = request.args.get('status', '')
    filtro_atrasadas = request.args.get('filtro') == 'atrasadas'

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True, buffered=True)

    try:
        cursor.execute("SELECT DISTINCT YEAR(data_transacao) as ano FROM transacoes WHERE usuario_id = %s ORDER BY ano DESC", [user_id])
        anos_disponiveis = [row['ano'] for row in cursor.fetchall()]

        query_base = " FROM transacoes t LEFT JOIN categorias c ON t.categoria_id = c.id WHERE t.usuario_id = %s"
        params = [user_id]

        if filtro_atrasadas:
            query_base += " AND t.pago = 0 AND t.data_transacao < %s"
            params.append(hoje)
            titulo_pagina = "Contas Pendentes (Atrasadas)"
        else:
            titulo_pagina = "Extrato de Transações"
            if mes_filtro:
                ano, mes = mes_filtro.split('-')
                query_base += " AND YEAR(t.data_transacao) = %s AND MONTH(t.data_transacao) = %s"
                params.extend([ano, mes])

        if busca:
            query_base += " AND t.descricao LIKE %s"
            params.append(f"%{busca}%")
        if metodo_filtro:
            query_base += " AND t.metodo = %s"
            params.append(metodo_filtro)
        if status_filtro:
            query_base += " AND t.pago = %s"
            params.append(status_filtro)

        sql_lista = "SELECT t.*, c.nome as categoria_nome, c.cor as categoria_cor " + query_base + " ORDER BY t.data_transacao DESC"
        cursor.execute(sql_lista, tuple(params))
        transacoes = cursor.fetchall()

        # --- LÓGICA MATEMÁTICA UNIFICADA ---
        
        # 1. Entradas (Tudo que é Receita)
        total_receitas = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'receita')

        # 2. Investimentos (Aporte Mensal)
        total_investimentos = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'investimento' and t['pago'] == 1)

        # 3. Gastos Reais (Apenas o que é Despesa)
        total_despesas_reais = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'despesa')

        # 4. Saldo Projetado (O que sobra: Receita - Despesa - Investimento)
        saldo_projetado = total_receitas - total_despesas_reais - total_investimentos

        # 5. Total Pago (Apenas das Despesas Reais)
        total_pago = sum(float(t['valor_total']) for t in transacoes if t['pago'] == 1 and t['tipo'].strip().lower() == 'despesa')

        # 6. Aguardando Pagamento (Apenas das Despesas Reais)
        total_pendente = sum(float(t['valor_total']) for t in transacoes if t['pago'] == 0 and t['tipo'].strip().lower() == 'despesa')

        # 7. Taxa de Investimento (Para a barra de progresso)
        taxa_invest = (total_investimentos / total_receitas * 100) if total_receitas > 0 else 0

        # --- STATUS E DIAGNÓSTICO ---
        taxa_investimento = (total_investimentos / total_receitas * 100) if total_receitas > 0 else 0
        
        if saldo_projetado < 0:
            status_financeiro, classe_alerta, sugestao = "Crítico", "text-danger", "Despesas superam receitas!"
        else:
            status_financeiro, classe_alerta, sugestao = "Saudável", "text-success", "Saldo positivo!"

    finally:
        cursor.close()
        conn.close()

    # --- RETORNO CORRIGIDO PARA O TEMPLATE ---
    return render_template('listagem.html', 
                           transacoes=transacoes,
                           total_receitas=total_receitas,
                           total_despesas=total_despesas_reais,
                           total_investimentos=total_investimentos,
                           saldo_atual=saldo_projetado,
                           total_pago=total_pago,
                           total_pendente=total_pendente,
                           titulo=titulo_pagina,
                           mes_ano_input=mes_filtro,
                           anos=anos_disponiveis,
                           datetime_now=agora)
    
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

def configurar_categorias_padrao(usuario_id):
    categorias_padrao = [
        ('Alimentação', '#e74c3c', 'Despesa'),
        ('Moradia', '#3498db', 'Despesa'),
        ('Transporte', '#f1c40f', 'Despesa'),
        ('Lazer', '#2ecc71', 'Despesa'),
        ('Saúde', '#9b59b6', 'Despesa'),
        ('Salário', '#27ae60', 'Receita'),
        ('Investimentos', '#bc1a93', 'Investimento')
    ]
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    query = "INSERT INTO categorias (nome, cor, tipo, usuario_id, is_sistema) VALUES (%s, %s, %s, %s, TRUE)"
    
    for cat in categorias_padrao:
        try:
            cursor.execute(query, (cat[0], cat[1], cat[2], usuario_id))
        except:
            continue # Ignora duplicatas caso existam
            
    conn.commit()
    cursor.close()
    conn.close()

# Gestão de Categorias
@app.route('/categorias')
def categorias():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    # Filtra por usuario_id para garantir que os links de editar/excluir funcionem
    cursor.execute("SELECT * FROM categorias WHERE usuario_id = %s ORDER BY nome", (session['usuario_id'],))
    lista_categorias = cursor.fetchall()
    
    cor_sugerida = gerar_cor_vibrante()

    cursor.close()
    conn.close()
    return render_template('categorias.html',
                           categorias=lista_categorias,
                           proxima_cor=cor_sugerida)

# Salvar Categoria
@app.route('/salvar_categoria', methods=['POST'])
def salvar_categoria():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    nome_cat = request.form.get('nome_categoria').strip().capitalize()
    cor = request.form.get('cor')
    tipo = request.form.get('tipo')
    usuario_id = session['usuario_id']
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    try:
        query = "INSERT INTO categorias (nome_cat, cor, tipo, usuario_id) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (nome_cat, cor, tipo, usuario_id))
        conn.commit()
        flash('Categoria adicionada com sucesso!', 'success')
    except mysql.connector.Error as err:
        if err.errno == 1062:
            # Busca novamente para renderizar a página com o erro
            cursor.execute("SELECT * FROM categorias WHERE usuario_id = %s ORDER BY nome", (usuario_id,))
            todas = cursor.fetchall()
            return render_template('categorias.html', categorias=todas, erro=f"A categoria '{nome_cat}' já existe!")
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('categorias'))

# Editar Categoria
@app.route('/editar_categoria/<int:id>', methods=['GET', 'POST'])
def editar_categoria(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nova_cor = request.form.get('cor')
        novo_tipo = request.form.get('tipo')
        usuario_id = session['usuario_id']

        # Verifica se é sistema
        cursor.execute("SELECT is_sistema, nome FROM categorias WHERE id = %s", (id,))
        cat_atual = cursor.fetchone()

        if cat_atual['is_sistema']:
            # Se for sistema, mantém o nome original, muda apenas cor e tipo
            query = "UPDATE categorias SET cor = %s, tipo = %s WHERE id = %s AND usuario_id = %s"
            params = (nova_cor, novo_tipo, id, usuario_id)
        else:
            # Se não for sistema, permite mudar o nome também
            novo_nome = request.form.get('nome_categoria').strip().capitalize()
            query = "UPDATE categorias SET nome = %s, cor = %s, tipo = %s WHERE id = %s AND usuario_id = %s"
            params = (novo_nome, nova_cor, novo_tipo, id, usuario_id)
        
        try:
            cursor.execute(query, params)
            conn.commit()
            flash('Categoria atualizada!', 'success')
        except mysql.connector.Error as err:
            flash(f"Erro ao atualizar: {err}", "erro")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('categorias'))

    # GET: Busca os dados
    cursor.execute("SELECT * FROM categorias WHERE id = %s AND usuario_id = %s", (id, session['usuario_id']))
    categoria = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('editar_categoria.html', categoria=categoria)

# Gera cores no formato HSL (Saturada e Brilhante) e converte ou usa padrões conhecidos
def gerar_cor_vibrante():
    cores_vibrantes = [
        '#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', "#bc1a93", 
        '#3498db', '#9b59b6', '#ff4757', '#2f3542', '#747d8c'
    ]
    return random.choice(cores_vibrantes)

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
@app.route('/excluir_categoria/<int:id>')
def excluir_categoria(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    try:
        # BUSCA para verificar se é sistema antes de deletar
        cursor.execute("SELECT is_sistema FROM categorias WHERE id = %s", (id,))
        cat = cursor.fetchone()
        
        if cat and cat['is_sistema']:
            flash('Categorias padrão do sistema não podem ser excluídas!', 'erro')
            return redirect(url_for('categorias'))

        cursor.execute("DELETE FROM categorias WHERE id = %s AND usuario_id = %s", (id, session['usuario_id']))
        conn.commit()
        flash('Categoria excluída com sucesso!', 'success')
    except mysql.connector.Error:
        flash('Não é possível excluir: existem transações usando esta categoria.', 'erro')
    finally:
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

# ROTA ÚNICA PARA PROCESSAR A ATUALIZAÇÃO (POST)
@app.route('/atualizar_transacao/<int:id>', methods=['POST'])
def atualizar_transacao(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    user_id = session['usuario_id']
    
    # 1. Captura de dados do formulário
    tipo = request.form.get('tipo', 'despesa')
    nova_descricao = request.form.get('descricao')
    nova_data = request.form.get('data_transacao')
    nova_categoria = request.form.get('categoria_id')
    tipo_edicao = request.form.get('tipo_edicao', 'individual')
    
    try:
        valor_raw = request.form.get('valor_total', '0').replace(',', '.')
        novo_valor = float(valor_raw)
    except:
        novo_valor = 0.0

    # 2. REGRA DE OURO: Lógica de Receita vs Despesa
    if tipo == 'receita':
        pago = 1           # Receita SEMPRE fica como paga/recebida
        novo_metodo = "Entrada"
    else:
        # Se for despesa, respeita o checkbox do formulário
        pago = 1 if request.form.get('pago') else 0
        novo_metodo = request.form.get('metodo') or 'Dinheiro'

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    try:
        # Busca registro para garantir que pertence ao usuário
        cursor.execute("SELECT * FROM transacoes WHERE id = %s", (id,))
        original = cursor.fetchone()

        if not original:
            flash("Registro não encontrado!", "erro")
            return redirect(url_for('listagem'))

        if tipo_edicao == 'grupo' and (original['id_transacao_pai'] or original['is_parcelado']):
            # Atualização em Grupo (Parcelas)
            id_pai = original['id_transacao_pai'] if original['id_transacao_pai'] else id
            novo_total_p = request.form.get('novo_total_parcelas')
            nome_limpo = nova_descricao.split(' (')[0].strip()
            
            sql = """
                UPDATE transacoes 
                SET descricao = CONCAT(%s, ' (', parcela_atual, '/', %s, ')'),
                    categoria_id = %s, metodo = %s, tipo = %s, pago = %s, numero_parcelas = %s
                WHERE (id = %s OR id_transacao_pai = %s) AND usuario_id = %s
            """
            cursor.execute(sql, (nome_limpo, novo_total_p, nova_categoria, novo_metodo, tipo, pago, novo_total_p, id_pai, id_pai, user_id))
        else:
            # Atualização Individual
            sql = """
                UPDATE transacoes 
                SET descricao = %s, valor_total = %s, data_transacao = %s, 
                    categoria_id = %s, metodo = %s, pago = %s, tipo = %s
                WHERE id = %s AND usuario_id = %s
            """
            cursor.execute(sql, (nova_descricao, novo_valor, nova_data, nova_categoria, novo_metodo, pago, tipo, id, user_id))

        conn.commit()
        flash("Atualizado com sucesso!", "sucesso")
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro ao salvar: {e}")
        flash("Erro ao processar atualização.", "erro")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('listagem'))

# Alternar Status de Pagamento
@app.route('/alternar_pagamento/<int:id>', methods=['POST'])
def alternar_pagamento(id):
    if 'usuario_id' not in session:
        return jsonify({'status': 'erro', 'mensagem': 'Não logado'}), 401
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True) # Usar dictionary=True facilita o acesso
    
    # 1. Busca o status atual E o tipo da transação
    cursor.execute("SELECT pago, tipo, data_transacao FROM transacoes WHERE id = %s", (id,))
    resultado = cursor.fetchone()
    
    if resultado:
        pago_atual = resultado['pago']
        tipo = resultado['tipo'].strip().lower()
        data_referencia = resultado['data_transacao']

        # 2. REGRA: Se for receita, status é sempre 1. Se despesa/investimento, inverte.
        novo_status = 1 if tipo == 'receita' else (0 if pago_atual == 1 else 1)
        cursor.execute("UPDATE transacoes SET pago = %s WHERE id = %s", (novo_status, id))
        conn.commit()

        # 3. RECALCULO COMPLETO (Baseado na sua nova lógica financeira)
        # Filtramos pelo mês da transação alterada para manter os cards do extrato corretos
        cursor.execute("""
            SELECT tipo, pago, valor_total 
            FROM transacoes 
            WHERE usuario_id = %s 
            AND MONTH(data_transacao) = %s 
            AND YEAR(data_transacao) = %s
        """, (session['usuario_id'], data_referencia.month, data_referencia.year))
        
        transacoes_mes = cursor.fetchall()
        
        # Processamento dos novos totais em Python (mais seguro para sua regra customizada)
        total_receita = sum(float(t['valor_total']) for t in transacoes_mes if t['tipo'].lower() == 'receita')
        total_investimentos_pagos = sum(float(t['valor_total']) for t in transacoes_mes if t['tipo'].lower() == 'investimento' and t['pago'] == 1)
        total_despesas_reais = sum(float(t['valor_total']) for t in transacoes_mes if t['tipo'].lower() == 'despesa')
        
        # Saldo Projetado: Receita - Despesa - Aporte Pago
        saldo_final = total_receita - total_despesas_reais - total_investimentos_pagos
        
        # Status de Pagamento (Apenas sobre despesas)
        total_pago = sum(float(t['valor_total']) for t in transacoes_mes if t['pago'] == 1 and t['tipo'].lower() == 'despesa')
        total_pendente = sum(float(t['valor_total']) for t in transacoes_mes if t['pago'] == 0 and t['tipo'].lower() == 'despesa')

        cursor.close()
        conn.close()

        # 4. RESPOSTA JSON PARA O JAVASCRIPT
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'sucesso',
                'novo_receita': total_receita,
                'novo_despesa': total_despesas_reais,
                'novo_aporte': total_investimentos_pagos,
                'novo_saldo': saldo_final,
                'novo_pago': total_pago,
                'novo_pendente': total_pendente,
                'status_financeiro': "Saudável" if saldo_final >= 0 else "Crítico",
                'sugestao': "Seu orçamento está equilibrado." if saldo_final >= 0 else "Suas saídas superaram as entradas este mês."
            })

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

@app.route('/exportar_excel')
def exportar_excel():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    user_id = session['usuario_id']
    mes_filtro = request.args.get('mes_filtro', '')
    ano_filtro = request.args.get('ano_filtro', '')
    busca = request.args.get('busca', '')
    metodo_filtro = request.args.get('metodo', '')
    status_filtro = request.args.get('status', '')

    if not any([mes_filtro, ano_filtro, request.args.get('busca')]):
        mes_filtro = datetime.now().strftime('%Y-%m')

    # 1. Nome dinâmico do arquivo
    if mes_filtro:
        ano_f, mes_f = mes_filtro.split('-')
        nome_arquivo = f"Extrato_{obter_nome_mes(mes_f)}_{ano_f}.xlsx"
    elif ano_filtro:
        nome_arquivo = f"Extrato_Ano_{ano_filtro}.xlsx"
    else:
        nome_arquivo = "Extrato_Geral.xlsx"

    # 2. Query SQL idêntica à listagem para manter consistência
    query = "SELECT data_transacao, descricao, metodo_pagamento, valor_total, pago FROM transacoes WHERE usuario_id = %s"
    params = [user_id]

    if mes_filtro:
        ano, mes = mes_filtro.split('-')
        query += " AND YEAR(data_transacao) = %s AND MONTH(data_transacao) = %s"
        params.extend([ano, mes])
    elif ano_filtro:
        query += " AND YEAR(data_transacao) = %s"
        params.append(ano_filtro)
    
    if busca:
        query += " AND descricao LIKE %s"
        params.append(f"%{busca}%")
    if metodo_filtro:
        query += " AND metodo_pagamento = %s"
        params.append(metodo_filtro)
    if status_filtro:
        query += " AND pago = %s"
        params.append(status_filtro)

    # 3. Busca de dados
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, tuple(params))
    dados_brutos = cursor.fetchall()
    cursor.close()
    conn.close()

    if not dados_brutos:
        return "<script>alert('Sem dados para exportar.'); window.history.back();</script>"

    # 4. Gerando o Excel com Pandas e XlsxWriter
    df = pd.DataFrame(dados_brutos)
    df['data_transacao'] = pd.to_datetime(df['data_transacao'])
    df['status'] = df['pago'].map({1: 'PAGO', 0: 'PENDENTE'})
    df_final = df[['data_transacao', 'descricao', 'metodo_pagamento', 'valor_total', 'status']]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter', datetime_format='dd/mm/yyyy') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Extrato', startrow=1, header=False)
        workbook = writer.book
        worksheet = writer.sheets['Extrato']

        # Formatos
        fmt_moeda = workbook.add_format({'num_format': 'R$ #,##0.00'})
        fmt_pago = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        fmt_pendente = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        fmt_resumo_label = workbook.add_format({'bold': True, 'align': 'right', 'border': 1, 'bg_color': '#F2F2F2'})
        fmt_resumo_val = workbook.add_format({'num_format': 'R$ #,##0.00', 'bold': True, 'border': 1})

        # Estilizar Tabela
        (max_row, max_col) = df_final.shape
        worksheet.add_table(0, 0, max_row, max_col - 1, {
            'columns': [{'header': 'DATA'}, {'header': 'DESCRIÇÃO'}, {'header': 'MÉTODO'}, 
                        {'header': 'VALOR', 'format': fmt_moeda}, {'header': 'STATUS'}],
            'style': 'Table Style Medium 2'
        })
        
        # Formatação Condicional do Status
        worksheet.conditional_format(1, 4, max_row, 4, {'type': 'cell', 'criteria': '==', 'value': '"PAGO"', 'format': fmt_pago})
        worksheet.conditional_format(1, 4, max_row, 4, {'type': 'cell', 'criteria': '==', 'value': '"PENDENTE"', 'format': fmt_pendente})

        # --- CONSOLIDADO NO FINAL COM CORES ---
        linha_resumo = max_row + 3
        total_g = df['valor_total'].sum()
        total_pa = df[df['pago'] == 1]['valor_total'].sum()
        total_pe = df[df['pago'] == 0]['valor_total'].sum()

        # Criando formatos coloridos para o resumo
        fmt_resumo_pago = workbook.add_format({'num_format': 'R$ #,##0.00', 'bold': True, 'font_color': '#006100', 'bg_color': '#C6EFCE', 'border': 1})
        fmt_resumo_pendente = workbook.add_format({'num_format': 'R$ #,##0.00', 'bold': True, 'font_color': '#9C0006', 'bg_color': '#FFC7CE', 'border': 1})
        fmt_resumo_geral = workbook.add_format({'num_format': 'R$ #,##0.00', 'bold': True, 'bg_color': '#D9E1F2', 'border': 1})

        # Escrita dos Totais
        worksheet.write(linha_resumo, 3, 'GASTO DO MÊS:', fmt_resumo_label)
        worksheet.write(linha_resumo, 4, total_g, fmt_resumo_geral)
        
        worksheet.write(linha_resumo + 1, 3, 'VALOR PAGO:', fmt_resumo_label)
        worksheet.write(linha_resumo + 1, 4, total_pa, fmt_resumo_pago)
        
        worksheet.write(linha_resumo + 2, 3, 'VALOR PENDENTE:', fmt_resumo_label)
        worksheet.write(linha_resumo + 2, 4, total_pe, fmt_resumo_pendente)
        
        # Ajuste de colunas
        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 40)
        worksheet.set_column('C:E', 18)

    output.seek(0)
    return send_file(output, as_attachment=True, download_name=nome_arquivo, 
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route('/ajuda')
def ajuda():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('ajuda.html')







if __name__ == '__main__':
    app.run(debug=True)