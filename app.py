from flask import Flask, flash, jsonify, render_template, request, redirect, url_for, session, send_file
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import os
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

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

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
    
# CONFIGURAÇÃO DO SEU BANCO
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'auth_plugin': 'mysql_native_password'
}

# Configurações do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ('Gestão Financeira', os.getenv('EMAIL_USER'))

mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)

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
        
        # 2. PEGA O ID do usuário que acabou de ser criado (ESSENCIAL vir antes)
        novo_usuario_id = cursor.lastrowid
        
        # 3. CHAMA A FUNÇÃO DE CATEGORIAS PADRÃO
        # Ela agora centraliza toda a lógica de criação inicial
        configurar_categorias_padrao(cursor, novo_usuario_id)
        
        conn.commit()
        flash("Conta criada com sucesso! Agora você já pode entrar.", "sucesso")
        return redirect(url_for('login'))

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        if err.errno == 1062: # Código de erro para duplicata no MySQL
            flash("Este e-mail já está cadastrado!", "erro")
            return redirect(url_for('cadastrar_page')) # Substitua pela sua rota de GET cadastro
        return f"Erro ao cadastrar: {str(err)}"
    finally:
        if conn:
            cursor.close()
            conn.close()

def configurar_categorias_padrao(cursor, usuario_id):
    categorias_padrao = [
        ('Salário', '#27ae60', 'receita'),
        ('Alimentação', '#e74c3c', 'despesa'),
        ('Moradia', '#6a10be', 'despesa'),
        ('Transporte', '#f1c40f', 'despesa'),
        ('Lazer', '#1c4938', 'despesa'),
        ('Saúde', '#9b59b6', 'despesa'),
        ('Investimentos', '#3498db', 'investimento')
    ]
    
    for nome, cor, tipo in categorias_padrao:
        # Só insere se não existir (evita duplicatas se a função for chamada no login)
        cursor.execute("SELECT id FROM categorias WHERE nome = %s AND usuario_id = %s", (nome, usuario_id))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO categorias (nome, cor, tipo, usuario_id, is_sistema) VALUES (%s, %s, %s, %s, TRUE)",
                (nome, cor, tipo, usuario_id)
            )
   
# Perfil do usuário
@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    user_id = session['usuario_id']
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')

        cursor.execute("SELECT senha FROM usuarios WHERE id = %s", (user_id,))
        usuario = cursor.fetchone()

        # Verifica se a senha atual está correta
        if usuario and check_password_hash(usuario['senha'], senha_atual):
            if nova_senha: # Se digitou nova senha, criptografa ela
                senha_final = generate_password_hash(nova_senha)
            else: # Se não, mantém a atual
                senha_final = usuario['senha']

            cursor.execute("""
                UPDATE usuarios SET nome = %s, email = %s, senha = %s 
                WHERE id = %s
            """, (nome, email, senha_final, user_id))
            conn.commit()
            session['usuario_nome'] = nome # Atualiza o nome na sessão para mudar no topo
            flash('Perfil atualizado com sucesso!', 'sucesso')
        else:
            flash('Senha atual incorreta!', 'erro')

        if usuario and check_password_hash(usuario['senha'], senha_atual):
            if nova_senha:
                senha_final = generate_password_hash(nova_senha)
                cursor.execute("UPDATE usuarios SET nome=%s, email=%s, senha=%s WHERE id=%s", (nome, email, senha_final, user_id))
                conn.commit()
                session.clear() # Limpa a sessão para forçar novo login com a senha nova
                flash('Senha alterada com sucesso! Por favor, faça login novamente.', 'sucesso')
                return redirect(url_for('login'))
            else:
                cursor.execute("UPDATE usuarios SET nome=%s, email=%s WHERE id=%s", (nome, email, user_id))
                conn.commit()
                session['usuario_nome'] = nome
                flash('Perfil atualizado com sucesso!', 'sucesso')
                return redirect(url_for('perfil'))

    cursor.execute("SELECT nome, email FROM usuarios WHERE id = %s", (user_id,))
    usuario_dados = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('perfil.html', usuario=usuario_dados)

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

# Esqueceu a senha
# --- Pedir recuperação ---
@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email')
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            # Gera um token que expira em 30 minutos (1800 segundos)
            token = s.dumps(email, salt='recuperar-senha')
            link = url_for('redefinir_senha', token=token, _external=True)
            
            # Envia o e-mail
            msg = Message('Recuperação de Senha - Gestão Financeira', recipients=[email])
            msg.body = f'Para redefinir a sua senha, clique no link: {link}\nEste link expira em 30 minutos.'
            mail.send(msg)
            
            flash('Enviámos um link de recuperação para o seu e-mail.', 'success')
            return redirect(url_for('login'))
        else:
            flash('E-mail não encontrado.', 'danger')
            
    return render_template('esqueci_senha.html')

# --- Redefinir a senha com o Token ---
@app.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    try:
        # Tenta ler o e-mail do token (valida se não expirou)
        email = s.loads(token, salt='recuperar-senha', max_age=1800)
    except:
        flash('O link de recuperação é inválido ou expirou.', 'danger')
        return redirect(url_for('esqueci_senha'))

    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha').strip()
        senha_hash = generate_password_hash(nova_senha)
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE usuarios SET senha = %s WHERE email = %s", (senha_hash, email))
        conn.commit()
        
        flash('Senha atualizada com sucesso!', 'success')
        return redirect(url_for('login'))

    return render_template('redefinir_senha_final.html')

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

        # --- LÓGICA MATEMÁTICA ---
        total_receitas = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'receita')
        total_investimentos = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'investimento' and t['pago'] == 1)
        total_despesas = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'despesa')

        # Saldo Projetado
        saldo_projetado = total_receitas - total_despesas - total_investimentos
        
        total_pago = sum(float(t['valor_total']) for t in transacoes if t['pago'] == 1 and t['tipo'].strip().lower() == 'despesa')
        total_pendente = sum(float(t['valor_total']) for t in transacoes if t['pago'] == 0 and t['tipo'].strip().lower() == 'despesa')

        # Percentual de Gasto (CORRIGIDO: total_despesas_reais)
        percentual_gasto = (total_despesas / total_receitas * 100) if total_receitas > 0 else 0

        # --- STATUS E DIAGNÓSTICO (UNIFICADO COM A LISTAGEM) ---
        if saldo_projetado < 0:
            status_financeiro = "Crítico"
            sugestao = "Suas saídas superaram as entradas. Revise seus custos urgentemente."
        elif percentual_gasto > 80:
            status_financeiro = "Atenção"
            sugestao = "Você já comprometeu mais de 80% da sua receita. Cuidado com novos gastos."
        else:
            status_financeiro = "Saudável"
            sugestao = "Seu orçamento está equilibrado e você está dentro da meta."

        # Taxa de Investimento para a barra
        taxa_invest = (total_investimentos / total_receitas * 100) if total_receitas > 0 else 0

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
            SUM(CASE WHEN tipo = 'investimento' AND pago = 1 THEN valor_total ELSE 0 END) as inv
            FROM transacoes 
            WHERE usuario_id = %s AND YEAR(data_transacao) = %s
            GROUP BY MONTH(data_transacao) 
            ORDER BY MONTH(data_transacao)
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
        total_despesas=total_despesas,
        saldo_atual=saldo_projetado,
        total_pago=total_pago,
        total_pendente=total_pendente,
        total_investimentos=total_investimentos,
        taxa_investimento=taxa_invest,
        status_financeiro=status_financeiro,
        sugestao=sugestao,
        labels=labels,
        valores=valores,
        cores=cores,
        percentual_gasto=percentual_gasto,
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
        user_id = session['usuario_id']
        descricao = request.form.get('descricao')
        valor_bruto = request.form.get('valor_total', '0').replace(',', '.')
        categoria_id = request.form.get('categoria_id')
        data_str = request.form.get('data_transacao')
        tipo = request.form.get('tipo', 'despesa')
        metodo = request.form.get('metodo') or 'Dinheiro'
        
        # 1. Captura número de parcelas (se não houver, assume 1)
        try:
            num_parcelas = int(request.form.get('numero_parcelas', 1))
        except:
            num_parcelas = 1

        try:
            valor_total = float(valor_bruto)
            data_base = datetime.strptime(data_str, '%Y-%m-%d')
        except:
            valor_total = 0.0
            data_base = datetime.now()

        # 2. Regra de Ouro: Ajustada para Investimentos e Checkboxes
        tipo = request.form.get('tipo')

        if tipo == 'receita':
            # Receita sempre nasce paga automaticamente
            pago = 1
        else:
            # O checkbox 'pago' só existe no request.form se estiver MARCADO.
            # Usamos bool() ou comparamos a existência para garantir Despesa/Investimento.
            pago = 1 if request.form.get('pago') else 0
            
        try:
            # LÓGICA DE PARCELAMENTO (Apenas para Despesa no Cartão > 1 parcela)
            if tipo == 'despesa' and metodo == 'Cartão de Crédito' and num_parcelas > 1:
                valor_parcela_base = round(valor_total / num_parcelas, 2)
                diferenca = round(valor_total - (valor_parcela_base * num_parcelas), 2)
                
                id_pai = None
                for i in range(1, num_parcelas + 1):
                    # Ajuste de centavos na última parcela
                    valor_atual = round(valor_parcela_base + diferenca, 2) if i == num_parcelas else valor_parcela_base
                    
                    # Incrementa um mês para cada parcela
                    data_parcela = (data_base + relativedelta(months=i-1)).strftime('%Y-%m-%d')
                    desc_parcela = f"{descricao} ({i}/{num_parcelas})"
                    
                    sql = """INSERT INTO transacoes 
                             (usuario_id, descricao, valor_total, tipo, categoria_id, data_transacao, 
                              pago, metodo, id_transacao_pai, parcela_atual, numero_parcelas, is_parcelado) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)"""
                    
                    cursor.execute(sql, (user_id, desc_parcela, valor_atual, tipo, categoria_id, 
                                         data_parcela, pago, metodo, id_pai, i, num_parcelas))
                    
                    # Define o ID da primeira parcela como pai das outras
                    if i == 1:
                        id_pai = cursor.lastrowid
            
            else:
                # LANÇAMENTO ÚNICO (Receita ou Despesa à vista)
                sql = """INSERT INTO transacoes (usuario_id, descricao, valor_total, tipo, 
                         categoria_id, data_transacao, pago, metodo, is_parcelado) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE)"""
                cursor.execute(sql, (user_id, descricao, valor_total, tipo, 
                                     categoria_id, data_str, pago, metodo))

            conn.commit()
            flash("Lançamento realizado com sucesso!", "sucesso")
        except Exception as e:
            print(f"ERRO AO GRAVAR: {e}")
            conn.rollback()
            flash("Erro ao salvar lançamento.", "erro")
        finally:
            cursor.close()
            conn.close()
            
        return redirect(url_for('novo_lancamento'))

    # GET: Busca categorias para o select
    cursor.execute("""
        SELECT id, nome, tipo, cor 
        FROM categorias 
        WHERE usuario_id = %s 
        ORDER BY nome ASC
    """, (session['usuario_id'],))
    
    categorias = cursor.fetchall()
    cursor.close()
    conn.close()
    
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
    mes_filtro = request.args.get('mes_filtro', '') 
    ano_filtro = request.args.get('ano_filtro', '')
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
            mes_atual_pt = "Atrasados"
        else:
            titulo_pagina = "Extrato de Transações"
            if mes_filtro and '-' in mes_filtro:
                ano, mes = mes_filtro.split('-')
                query_base += " AND YEAR(t.data_transacao) = %s AND MONTH(t.data_transacao) = %s"
                params.extend([ano, mes])
                meses_br = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
                            7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
                mes_atual_pt = meses_br.get(int(mes), "Extrato")
            elif ano_filtro:
                query_base += " AND YEAR(t.data_transacao) = %s"
                params.append(ano_filtro)
                mes_atual_pt = f"Ano {ano_filtro}"
            else:
                query_base += " AND YEAR(t.data_transacao) = %s AND MONTH(t.data_transacao) = %s"
                params.extend([agora.year, agora.month])
                mes_atual_pt = "Mês Atual"

        if busca:
            query_base += " AND t.descricao LIKE %s"
            params.append(f"%{busca}%")
        if metodo_filtro:
            query_base += " AND t.metodo = %s"
            params.append(metodo_filtro)
        if status_filtro:
            query_base += " AND t.pago = %s"
            params.append(status_filtro)

        sql_lista = """
            SELECT t.*, c.nome as categoria_nome, c.cor as categoria_cor,
            CASE 
                WHEN t.tipo = 'receita' THEN 1
                WHEN t.tipo = 'despesa' THEN 2
                WHEN t.tipo = 'investimento' THEN 3
                ELSE 4
            END AS ordem_tipo
        """ + query_base + " ORDER BY ordem_tipo ASC, t.data_transacao DESC"
        
        cursor.execute(sql_lista, tuple(params))
        transacoes = cursor.fetchall()

        # --- LÓGICA MATEMÁTICA ---
        total_receitas = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'receita')
        total_despesas = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'despesa')
        total_invest_pagos = sum(float(t['valor_total']) for t in transacoes if t['tipo'].strip().lower() == 'investimento' and t['pago'] == 1)
        
        saldo_projetado = total_receitas - total_despesas - total_invest_pagos
        
        total_pago = sum(float(t['valor_total']) for t in transacoes if t['pago'] == 1 and t['tipo'].strip().lower() == 'despesa')
        total_pendente = sum(float(t['valor_total']) for t in transacoes if t['pago'] == 0 and t['tipo'].strip().lower() == 'despesa')
        percentual_gasto = (total_despesas / total_receitas * 100) if total_receitas > 0 else 0

        # --- STATUS E DIAGNÓSTICO ---
        if saldo_projetado < 0:
            status_financeiro = "Crítico"
            sugestao = "Suas saídas superaram as entradas. Revise seus custos urgentemente."
        elif percentual_gasto > 80:
            status_financeiro = "Atenção"
            sugestao = "Você já comprometeu mais de 80% da sua receita. Cuidado com novos gastos."
        else:
            status_financeiro = "Saudável"
            sugestao = "Seu orçamento está equilibrado e você está dentro da meta."

        cursor.execute("SELECT * FROM categorias WHERE usuario_id = %s ORDER BY nome", (user_id,))
        categorias = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template('listagem.html', 
                           transacoes=transacoes,
                           total_receitas=total_receitas,
                           total_despesas=total_despesas,
                           total_investimentos=total_invest_pagos,
                           saldo_atual=saldo_projetado,  # Enviando como saldo_atual para o HTML
                           saldo_p=saldo_projetado,      # Enviando como saldo_p para garantir a cor
                           total_pago=total_pago,
                           total_pendente=total_pendente,
                           percentual_gasto=percentual_gasto,
                           status_financeiro=status_financeiro,
                           sugestao=sugestao,
                           titulo=titulo_pagina,
                           mes_ano_input=mes_filtro,
                           ano_selecionado=ano_filtro,
                           mes_atual_pt=mes_atual_pt,
                           anos=anos_disponiveis,
                           datetime_now=agora,
                           categorias=categorias)

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
    
    # Query atualizada com ordem personalizada por TIPO
    sql = """
        SELECT *, 
        CASE 
            WHEN tipo = 'receita' THEN 1
            WHEN tipo = 'despesa' THEN 2
            WHEN tipo = 'investimento' THEN 3
            ELSE 4
        END AS ordem_tipo
        FROM categorias 
        WHERE usuario_id = %s 
        ORDER BY ordem_tipo ASC, nome ASC
    """
    cursor.execute(sql, (session['usuario_id'],))
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
    
    # O HTML envia 'nome_categoria', capturamos e limpamos
    nome_input = request.form.get('nome_categoria').strip().capitalize()
    cor = request.form.get('cor')
    tipo = request.form.get('tipo')
    usuario_id = session['usuario_id']
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    try:
        # CORREÇÃO: O nome da coluna no banco é 'nome' e não 'nome_cat'
        # Adicionamos is_sistema = 0 explicitamente
        query = "INSERT INTO categorias (nome, cor, tipo, usuario_id, is_sistema) VALUES (%s, %s, %s, %s, 0)"
        cursor.execute(query, (nome_input, cor, tipo, usuario_id))
        conn.commit()
        flash('Categoria adicionada com sucesso!', 'sucesso') # Use 'sucesso' para bater com o CSS
    except mysql.connector.Error as err:
        if err.errno == 1062:
            flash(f"A categoria '{nome_input}' já existe!", 'erro')
        else:
            flash(f"Erro ao salvar: {err}", 'erro')
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

    # 1. Busca a categoria e verifica se existe
    cursor.execute("SELECT is_sistema, nome FROM categorias WHERE id = %s", (id,))
    cat = cursor.fetchone()

    if not cat:
        flash('Categoria não encontrada.', 'erro')
    elif cat['is_sistema'] == 1:
        flash(f'A categoria "{cat["nome"]}" é protegida pelo sistema e não pode ser removida.', 'erro')
        cursor.close()
        conn.close()
        return redirect(url_for('categorias'))
    else:
        # 2. VERIFICAÇÃO DE SEGURANÇA: Contar transações vinculadas
        cursor.execute("SELECT COUNT(*) as total FROM transacoes WHERE categoria_id = %s", (id,))
        uso = cursor.fetchone()
        
        if uso['total'] > 0:
            # Mensagem de erro que impede a exclusão acidental
            flash(f'Segurança: A categoria "{cat["nome"]}" possui {uso["total"]} transações vinculadas. Altere ou apague as transações primeiro.', 'erro')
        else:
            # 3. Exclusão permitida apenas se estiver vazia
            cursor.execute("DELETE FROM categorias WHERE id = %s", (id,))
            conn.commit()
            flash('Categoria removida com sucesso!', 'sucesso')

    cursor.close()
    conn.close()
    return redirect(url_for('categorias'))

# Mover todas as transações de uma categoria para outra (Tela de Categoria)
@app.route('/mover_transacoes', methods=['POST'])
def mover_transacoes():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    id_origem = request.form.get('id_origem')
    id_destino = request.form.get('id_destino')
    user_id = session['usuario_id']

    if not id_destino:
        flash('Você precisa selecionar uma categoria de destino!', 'erro')
        return redirect(url_for('categorias'))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    try:
        # Atualiza todas as transações da categoria A para a categoria B
        query = "UPDATE transacoes SET categoria_id = %s WHERE categoria_id = %s AND usuario_id = %s"
        cursor.execute(query, (id_destino, id_origem, user_id))
        
        # Conta quantas foram movidas para informar o usuário
        linhas_afetadas = cursor.rowcount
        conn.commit()
        
        flash(f'Sucesso! {linhas_afetadas} transações foram movidas com sucesso.', 'sucesso')
    except mysql.connector.Error as err:
        flash(f'Erro ao mover transações: {err}', 'erro')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('categorias'))

# Mover transações selecionadas de uma categoria para outra (Tela de Listagem)
@app.route('/mover_transacoes_selecionadas', methods=['POST'])
def mover_transacoes_selecionadas():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Recebe a lista de IDs do formulário
    transacoes_ids = request.form.getlist('transacoes_selecionadas')
    id_destino = request.form.get('id_destino')
    user_id = session['usuario_id']

    if not transacoes_ids:
        flash('Nenhuma transação selecionada.', 'erro')
        return redirect(url_for('listagem'))
    
    if not id_destino:
        flash('Selecione uma categoria de destino.', 'erro')
        return redirect(url_for('listagem'))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    try:
        # Cria a query dinamicamente para os IDs selecionados
        format_strings = ','.join(['%s'] * len(transacoes_ids))
        query = f"UPDATE transacoes SET categoria_id = %s WHERE id IN ({format_strings}) AND usuario_id = %s"
        
        # O primeiro parâmetro é o destino, os outros são os IDs, e o último o user_id
        params = [id_destino] + transacoes_ids + [user_id]
        
        cursor.execute(query, params)
        conn.commit()
        flash(f'{cursor.rowcount} transações movidas com sucesso!', 'sucesso')
    except Exception as e:
        flash(f'Erro ao mover: {str(e)}', 'erro')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('listagem'))

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
    
    # 1. Captura de dados básicos
    tipo = request.form.get('tipo', 'despesa')
    nova_descricao = request.form.get('descricao')
    nova_data = request.form.get('data_transacao')
    nova_categoria = request.form.get('categoria_id')
    tipo_edicao = request.form.get('tipo_edicao', 'individual')
    
    try:
        valor_raw = request.form.get('valor_total', '0').replace(',', '.')
        novo_valor_total = float(valor_raw)
    except:
        novo_valor_total = 0.0

    # 2. Regra de Negócio: Método e Status
    if tipo == 'receita':
        pago = 1
        novo_metodo = "Entrada"
    else:
        pago = 1 if request.form.get('pago') else 0
        novo_metodo = request.form.get('metodo') or 'Dinheiro'

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    try:
        # Busca registro original
        cursor.execute("SELECT * FROM transacoes WHERE id = %s AND usuario_id = %s", (id, user_id))
        original = cursor.fetchone()

        if not original:
            flash("Registro não encontrado!", "erro")
            return redirect(url_for('listagem'))

        # --- LÓGICA DE ATUALIZAÇÃO EM GRUPO (PARCELAS) ---
        if tipo_edicao == 'grupo' and (original['id_transacao_pai'] or original['is_parcelado']):
            id_pai = original['id_transacao_pai'] if original['id_transacao_pai'] else original['id']
            novo_total_p = int(request.form.get('novo_total_parcelas', original['numero_parcelas']))
            nome_limpo = nova_descricao.split(' (')[0].strip()

            # Cálculo de divisão justa (Ex: 100/3 = 33.33, 33.33, 33.34)
            valor_parcela_base = round(novo_valor_total / novo_total_p, 2)
            diferenca = round(novo_valor_total - (valor_parcela_base * novo_total_p), 2)

            # Buscamos todas as parcelas do grupo para atualizar uma a uma
            cursor.execute("SELECT id, parcela_atual FROM transacoes WHERE (id = %s OR id_transacao_pai = %s) AND usuario_id = %s", (id_pai, id_pai, user_id))
            parcelas_do_grupo = cursor.fetchall()

            for parcela in parcelas_do_grupo:
                # Se for a última parcela (ex: 3/3), recebe o ajuste de centavos
                if parcela['parcela_atual'] == novo_total_p:
                    valor_final_parcela = round(valor_parcela_base + diferenca, 2)
                else:
                    valor_final_parcela = valor_parcela_base

                desc_formatada = f"{nome_limpo} ({parcela['parcela_atual']}/{novo_total_p})"
                
                sql_grupo = """
                    UPDATE transacoes 
                    SET descricao = %s, valor_total = %s, categoria_id = %s, 
                        metodo = %s, tipo = %s, pago = %s, numero_parcelas = %s
                    WHERE id = %s
                """
                cursor.execute(sql_grupo, (desc_formatada, valor_final_parcela, nova_categoria, 
                                          novo_metodo, tipo, pago, novo_total_p, parcela['id']))

        # --- LÓGICA DE ATUALIZAÇÃO INDIVIDUAL ---
        else:
            sql_indiv = """
                UPDATE transacoes 
                SET descricao = %s, valor_total = %s, data_transacao = %s, 
                    categoria_id = %s, metodo = %s, pago = %s, tipo = %s
                WHERE id = %s AND usuario_id = %s
            """
            cursor.execute(sql_indiv, (nova_descricao, novo_valor_total, nova_data, 
                                      nova_categoria, novo_metodo, pago, tipo, id, user_id))

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
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT pago, tipo, data_transacao FROM transacoes WHERE id = %s", (id,))
        resultado = resultado = cursor.fetchone()
        
        if resultado:
            pago_atual = resultado['pago']
            tipo = resultado['tipo'].strip().lower()
            data_referencia = resultado['data_transacao']

            novo_status = 1 if tipo == 'receita' else (0 if pago_atual == 1 else 1)
            cursor.execute("UPDATE transacoes SET pago = %s WHERE id = %s", (novo_status, id))
            conn.commit()

            cursor.execute("""
                SELECT tipo, pago, valor_total 
                FROM transacoes 
                WHERE usuario_id = %s 
                AND MONTH(data_transacao) = %s 
                AND YEAR(data_transacao) = %s
            """, (session['usuario_id'], data_referencia.month, data_referencia.year))
            
            transacoes_mes = cursor.fetchall()
            
            # Cálculos
            total_receitas = sum(float(t['valor_total']) for t in transacoes_mes if t['tipo'].lower() == 'receita')
            total_investimentos = sum(float(t['valor_total']) for t in transacoes_mes if t['tipo'].lower() == 'investimento' and t['pago'] == 1)
            total_despesas = sum(float(t['valor_total']) for t in transacoes_mes if t['tipo'].lower() == 'despesa')
            
            saldo_projetado = total_receitas - total_despesas - total_investimentos
            total_pago = sum(float(t['valor_total']) for t in transacoes_mes if t['pago'] == 1 and t['tipo'].lower() == 'despesa')
            total_pendente = sum(float(t['valor_total']) for t in transacoes_mes if t['pago'] == 0 and t['tipo'].lower() == 'despesa')
            percentual_gasto = (total_despesas / total_receitas * 100) if total_receitas > 0 else 0

            # Lógica de Diagnóstico (Definição correta das variáveis)
            if saldo_projetado < 0:
                status_financeiro = "Crítico"
                sugestao = "Suas saídas superaram as entradas. Revise seus custos urgentemente."
            elif percentual_gasto > 80:
                status_financeiro = "Atenção"
                sugestao = "Você já comprometeu mais de 80% da sua receita. Cuidado com novos gastos."
            else:
                status_financeiro = "Saudável"
                sugestao = "Seu orçamento está equilibrado e você está dentro da meta."

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # RETORNO MAPEADO PARA O SEU JS (listagem.html)
                return jsonify({
                    'status': 'sucesso',
                    'novo_receita': total_receitas,
                    'novo_despesa': total_despesas,
                    'novo_saldo': saldo_projetado,
                    'novo_pago': total_pago,
                    'novo_pendente': total_pendente,
                    'novo_aporte': total_investimentos,
                    'status_financeiro': status_financeiro,
                    'sugestao': sugestao,
                    'percentual_gasto': percentual_gasto
                })

    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

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