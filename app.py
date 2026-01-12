from flask import Flask, flash, jsonify, render_template, request, redirect, url_for, session, send_file
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer as URLSafeTimeds
from dotenv import load_dotenv
from functools import wraps
from email_validator import validate_email, EmailNotValidError
from pywebpush import webpush, WebPushException
import re
import uuid
from ofxparse import OfxParser
from io import StringIO
import os
import io
import mysql.connector
import pandas as pd
import random
import locale
import json

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
s = URLSafeTimeds(app.secret_key)

VAPID_PRIVATE_KEY = os.getenv('PRIVATEKEY')
VAPID_EMAIL = "mailto:bcm.marra@gmail.com"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Por favor, faça login para acessar esta página.", "aviso")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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

DOMINIOS_PROIBIDOS = ['mailinator.com', '10minutemail.com', 'tempmail.com', 'guerrillamail.com']

def limpar_usuarios_pendentes(cursor):
    # Primeiro, buscamos os IDs dos usuários que serão limpos (ex: criados há mais de X horas e não ativos)
    # Aqui vou usar a lógica padrão de tempo que você já deve ter
    query_usuarios = "SELECT id FROM usuarios WHERE status_ativo = 0 AND data_criacao < NOW() - INTERVAL 24 HOUR"
    cursor.execute(query_usuarios)
    usuarios = cursor.fetchall()

    for (u_id,) in usuarios:
        # ORDEM DE EXCLUSÃO (Do filho para o pai)
        # 1. Apaga as regras de inteligência
        cursor.execute("DELETE FROM inteligencia_regras WHERE usuario_id = %s", (u_id,))
        
        # 2. Apaga as transações (caso existam)
        cursor.execute("DELETE FROM transacoes WHERE usuario_id = %s", (u_id,))
        
        # 3. Apaga as categorias
        cursor.execute("DELETE FROM categorias WHERE usuario_id = %s", (u_id,))
        
        # 4. Por fim, apaga o usuário
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (u_id,))
    
    print("Limpeza de pendentes concluída.")

def eh_email_suspeito(email):
    # Proíbe sequências comuns de teclado
    padroes_lixo = ['asdf', 'ghjk', '12345', 'qwerty']
    for padrao in padroes_lixo:
        if padrao in email:
            return True
    return False

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    nome = request.form.get('nome')
    email = request.form.get('email').strip().lower()
    senha_criptografada = generate_password_hash(request.form.get('senha'))    

    try:
        # Adicionamos um timeout de 5 segundos para não travar a tela
        valid = validate_email(email, check_deliverability=True, timeout=5)
        email = valid.email
    except EmailNotValidError as e:
        # O 'str(e)' explica EXATAMENTE por que o e-mail foi rejeitado
        flash(f"E-mail inválido: {str(e)}", "erro")
        return redirect(url_for('cadastro'))

    if eh_email_suspeito(email):
        flash("Por favor, use um e-mail válido e evite sequências aleatórias.", "erro")
        return redirect(url_for('cadastro'))

    # --- CAMADA 1: IMPEDIR E-MAILS TEMPORÁRIOS ---
    dominio = email.split('@')[-1]
    if dominio in DOMINIOS_PROIBIDOS:
        flash("E-mails temporários não são permitidos por segurança.", "erro")
        return redirect(url_for('cadastro'))

    # --- CAMADA 2: VALIDAÇÃO DE DOMÍNIO (FILTRO ANTI-LIXO) ---
    try:
        # check_deliverability=True verifica se o domínio tem servidores de e-mail reais
        valid = validate_email(email, check_deliverability=True)
        email = valid.email
    except EmailNotValidError:
        flash("O domínio deste e-mail não parece ser válido ou real.", "erro")
        return redirect(url_for('cadastro'))

    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        limpar_usuarios_pendentes(cursor)
        
        # 1. Insere o novo usuário (status_ativo já começa como 0 pelo DEFAULT do banco)
        sql_user = "INSERT INTO usuarios (nome, email, senha, status_ativo) VALUES (%s, %s, %s, 0)"
        cursor.execute(sql_user, (nome, email, senha_criptografada))
        
        novo_usuario_id = cursor.lastrowid
        configurar_categorias_padrao(cursor, novo_usuario_id)
        
        # --- PROCESSO DE E-MAIL ---
        token = s.dumps(email, salt='confirmacao-email')
        link_confirmacao = url_for('confirmar_email', token=token, _external=True)

        msg = Message('Ative sua conta - Descomplica MyFinance', recipients=[email])
        msg.html = f"""
            <h3>Olá, {nome}!</h3>
            <p>Obrigado por se cadastrar no <strong>Descomplica MyFinance</strong>.</p>
            <p>Para confirmar o seu cadastro, clique no link abaixo:</p>
            <p><a href="{link_confirmacao}" style="padding: 10px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">ATIVAR MINHA CONTA AGORA</a></p>
            <p><small>Este link expira em 30 minutos.</small></p>
        """
        mail.send(msg)
        # --------------------------

        conn.commit()
        flash("Conta criada! Verifique seu e-mail para ativar sua conta antes de entrar.", "sucesso")
        return redirect(url_for('login'))

    except mysql.connector.Error as err:
        if conn: conn.rollback()
        if err.errno == 1062:
            flash("Este e-mail já está cadastrado!", "erro")
        else:
            flash(f"Erro no banco: {err}", "erro")
        return redirect(url_for('cadastro'))
    finally:
        if conn:
            cursor.close()
            conn.close()

# --- ROTA DE ATIVAÇÃO ---
@app.route('/confirmar_email/<token>')
def confirmar_email(token):
    # O SEGREDO: Definir conn como None logo no início
    conn = None
    cursor = None
    
    try:
        # Tenta carregar o e-mail do token
        email = s.loads(token, salt='confirmacao-email', max_age=1800)
        
        # Só aqui tentamos conectar ao banco
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # 1. Verifica se já está ativo
        cursor.execute("SELECT status_ativo FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()
        
        if usuario and usuario['status_ativo'] == 1:
            flash("Este e-mail já foi verificado anteriormente!", "info")
            return redirect(url_for('login'))

        # 2. Ativa o usuário
        cursor.execute("UPDATE usuarios SET status_ativo = 1 WHERE email = %s", (email,))
        conn.commit()
        
        flash("E-mail confirmado com sucesso! Sua conta está ativa.", "sucesso")
        
    except Exception as e:
        print(f"Erro na ativação: {e}") # Ajuda a debugar no terminal
        flash("O link de confirmação expirou ou é inválido.", "erro")
    
    finally:
        # Agora o 'if conn' funciona, pois se falhar lá em cima, conn ainda é None
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('login'))

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
            
    cursor.execute("SELECT nome, email FROM usuarios WHERE id = %s", (user_id,))
    usuario_dados = cursor.fetchone()
    
    cursor.execute("""
        SELECT id, nome_dispositivo, data_criacao 
        FROM inscricoes_push 
        WHERE usuario_id = %s 
        ORDER BY data_criacao DESC
    """, (user_id,))
    meus_dispositivos = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('perfil.html', usuario=usuario_dados, dispositivos=meus_dispositivos)

# Notificações
@app.route('/salvar-inscricao', methods=['POST'])
def salvar_inscricao():
    if 'usuario_id' not in session:
        return jsonify({"erro": "Não logado"}), 401
    
    dados = request.get_json()
    sub_objeto = dados.get('subscription')
    subscription_json = json.dumps(sub_objeto) 
    
    nome_dispositivo = dados.get('nome_dispositivo', 'Computador')
    
    usuario_id = session.get('usuario_id') or session.get('user_id')
    if not usuario_id:
        return jsonify({"erro": "Sessão expirada. Faça login novamente."}), 401
    
    try:
        dados = request.get_json()
        
        # O JavaScript novo envia 'subscription' e 'nome_dispositivo'
        sub_data = dados.get('subscription')
        subscription_json = json.dumps(sub_data) 
        
        nome_dispositivo = dados.get('nome_dispositivo', 'Computador')
        usuario_id = session.get('usuario_id')

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        sql = "INSERT INTO inscricoes_push (usuario_id, nome_dispositivo, subscription_json) VALUES (%s, %s, %s)"
        cursor.execute(sql, (usuario_id, nome_dispositivo, subscription_json))
        
        conn.commit()
        return jsonify({"status": "sucesso"}), 200

    except Exception as e:
        print(f"Erro ao salvar: {e}")
        return jsonify({"erro": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

def verificar_e_enviar_alertas():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    hoje = date.today()
    # Buscamos apenas o que vence hoje, não está pago e ainda não foi avisado
    sql = """
        SELECT id, descricao, valor_total, usuario_id 
        FROM transacoes 
        WHERE data_transacao = %s AND pago = 0 AND alerta_enviado = 0
    """
    cursor.execute(sql, (hoje,))
    contas_vencendo = cursor.fetchall()

    for conta in contas_vencendo:
        # Busca dispositivos do usuário
        cursor.execute("SELECT subscription_json FROM inscricoes_push WHERE usuario_id = %s", (conta['usuario_id'],))
        dispositivos = cursor.fetchall()
        
        payload = {
            "title": "Conta Vence Hoje! 💸",
            "body": f"Não esqueça: {conta['descricao']} (R$ {conta['valor_total']}) vence hoje.",
            "url": "/listagem"
        }

        envio_com_sucesso = False
        for disp in dispositivos:
            try:
                webpush(
                    subscription_info=json.loads(disp['subscription_json']),
                    data=json.dumps(payload),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": "mailto:bcm.marra@gmail.com"},
                    content_encoding="aes128gcm"
                )
                envio_com_sucesso = True
            except Exception as e:
                print(f"Erro ao enviar para um dispositivo: {e}")

        # Marcar como enviado para nunca mais repetir essa conta específica
        if envio_com_sucesso:
            cursor.execute("UPDATE transacoes SET alerta_enviado = 1 WHERE id = %s", (conta['id'],))
            conn.commit()

    cursor.close()
    conn.close()

def verificar_e_enviar_alertas_oficial():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    hoje = date.today()
    # Busca contas do dia, não pagas e não avisadas
    sql = """
        SELECT id, descricao, valor_total, usuario_id 
        FROM transacoes 
        WHERE data_transacao = %s AND pago = 0 AND alerta_enviado = 0 
        AND tipo IN ('despesa', 'investimento')
    """
    cursor.execute(sql, (hoje,))
    contas = cursor.fetchall()

    # Agrupa contas por usuário para não mandar 10 pushes se ele tiver 10 contas
    usuarios_alerta = {}
    for c in contas:
        uid = c['usuario_id']
        if uid not in usuarios_alerta:
            usuarios_alerta[uid] = []
        usuarios_alerta[uid].append(c)

    for usuario_id, lista_contas in usuarios_alerta.items():
        # Busca dispositivos do usuário
        cursor.execute("SELECT id, subscription_json FROM inscricoes_push WHERE usuario_id = %s", (usuario_id,))
        dispositivos = cursor.fetchall()

        # Monta a mensagem visual
        qtd = len(lista_contas)
        if qtd == 1:
            titulo = "Vencimento Hoje! 💸"
            corpo = f"A conta '{lista_contas[0]['descricao']}' vence hoje (R$ {lista_contas[0]['valor_total']})."
        else:
            total_valor = sum(float(c['valor_total']) for c in lista_contas)
            titulo = f"{qtd} Contas Vencem Hoje! 📅"
            corpo = f"Você tem {qtd} pendências somando R$ {total_valor:.2f}. Não esqueça de pagar!"

        payload = {
            "title": titulo,
            "body": corpo,
            "url": "/listagem" # Redireciona para a lista
        }

        for disp in dispositivos:
            try:
                webpush(
                    subscription_info=json.loads(disp['subscription_json']),
                    data=json.dumps(payload),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": "mailto:bcm.marra@gmail.com"},
                    content_encoding="aes128gcm",
                    headers={"Urgency": "high", "TTL": "86400"} # Dura 24h se o PC estiver desligado
                )
            except Exception as e:
                print(f"Dispositivo {disp['id']} offline ou inválido.")

        # Marca todas essas contas como avisadas
        ids_contas = [c['id'] for c in lista_contas]
        format_strings = ','.join(['%s'] * len(ids_contas))
        cursor.execute(f"UPDATE transacoes SET alerta_enviado = 1 WHERE id IN ({format_strings})", tuple(ids_contas))
        conn.commit()

    cursor.close()
    conn.close()

# Rota para deletar um dispositivo
@app.route('/remover-dispositivo/<int:id>', methods=['DELETE'])
def remover_dispositivo(id):
    usuario_id = session.get('usuario_id') or session.get('user_id')
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    # Segurança: garante que o usuário só delete o próprio dispositivo
    cursor.execute("DELETE FROM inscricoes_push WHERE id = %s AND usuario_id = %s", (id, usuario_id))
    conn.commit()
    
    return jsonify({"status": "sucesso"})

# Excluir conta do usuário
@app.route('/excluir_conta', methods=['POST'])
def excluir_conta():
    uid = session.get('usuario_id')
    senha_digitada = request.form.get('senha_confirmacao')
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # 1. Verifica a senha
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (uid,))
    usuario = cursor.fetchone()
    
    if usuario and check_password_hash(usuario['senha'], senha_digitada):
        # 2. Define data de exclusão (hoje + 30 dias) e status_ativo = 0
        data_exclusao = datetime.now() + timedelta(days=30)
        
        cursor.execute("""
            UPDATE usuarios 
            SET status_ativo = 0, data_exclusao_programada = %s 
            WHERE id = %s
        """, (data_exclusao, uid))
        
        conn.commit()
        session.clear() # Desloga o usuário
        
        flash("Sua conta foi inativada. Ela será excluída permanentemente em 30 dias se você não logar novamente.", "warning")
        return redirect(url_for('login'))
    else:
        flash("Senha incorreta. A conta não foi alterada.", "danger")
        return redirect(url_for('perfil'))
        
# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        limpar_usuarios_pendentes(cursor) # A função que criamos
        conn.commit()
    except Exception as e:
        print(f"Erro na limpeza: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()
            
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
        
            # 1. Verifica se a conta está aguardando ativação de e-mail (Novo Cadastro)
            # Supondo que você use um campo como 'confirmado_email' ou similar
            # Se você usa o status_ativo para os dois casos, a lógica abaixo resolve:
            
            if usuario.get('status_ativo') == 0:
                # Se ele tem uma data de exclusão, é uma REATIVAÇÃO
                if usuario.get('data_exclusao_programada'):
                    conn_react = mysql.connector.connect(**db_config)
                    cursor_react = conn_react.cursor()
                    cursor_react.execute("""
                        UPDATE usuarios 
                        SET status_ativo = 1, data_exclusao_programada = NULL, aviso_exclusao_enviado = 0 
                        WHERE id = %s
                    """, (usuario['id'],))
                    conn_react.commit()
                    cursor_react.close()
                    conn_react.close()
                    flash("Bem-vindo de volta! Sua solicitação de exclusão foi cancelada.", "success")
                    # Após reativar, deixamos o código seguir para logar ele normalmente
                else:
                    # Se não tem data de exclusão e está inativo, é conta nova não confirmada
                    return render_template('login.html', 
                        erro="Sua conta ainda não foi ativada. Verifique seu e-mail para confirmar o cadastro.")

            # 2. Loga o usuário normalmente
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            
            try:
                verificar_e_enviar_alertas_oficial()
            except Exception as e:
                print(f"Erro no disparo automático: {e}")
            
            return redirect(url_for('index'))

        else:
            # Caso a senha ou email estejam errados
            return render_template('login.html', erro="E-mail ou senha incorretos")
                    
            # Caso seja um GET (acesso inicial à página)
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
        
        # Fecha as conexões
        cursor.close()
        conn.close()
        
        flash('Senha atualizada com sucesso!', 'success')
        return redirect(url_for('login'))

    # Adicionamos o esconder_botoes=True aqui para o base.html reconhecer
    return render_template('redefinir_senha_final.html', esconder_botoes=True)

# Página Inicial
@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if 'usuario_id' in session:
        verificar_e_enviar_alertas()
               
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
            ORDER BY data_transacao ASC LIMIT 10
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

        metas_progresso = obter_progresso_metas(session['usuario_id'])

        def obter_dados_grafico_metas(user_id):
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            
            # Soma gastos por categoria no mês atual
            query = """
                SELECT c.nome, SUM(t.valor_total) as total
                FROM transacoes t
                JOIN categorias c ON t.categoria_id = c.id
                WHERE t.usuario_id = %s AND t.tipo = 'despesa'
                AND MONTH(t.data_transacao) = MONTH(CURRENT_DATE())
                AND YEAR(t.data_transacao) = YEAR(CURRENT_DATE())
                GROUP BY c.nome
            """
            cursor.execute(query, (user_id,))
            dados = cursor.fetchall()
            
            # Prepara os labels e valores para o Chart.js
            labels = [item['nome'] for item in dados]
            valores = [float(item['total']) for item in dados]
            
            cursor.close()
            conn.close()
            return labels, valores
        
        labels, valores = obter_dados_grafico_metas(user_id)

    finally:
        cursor.close()
        conn.close()


    return render_template('index.html',
        nome=session.get('usuario_nome'),
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
        valores_metodos=valores_metodos,
        metas=metas_progresso, 
        grafico_labels=labels, 
        grafico_valores=valores)
    
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
        is_recorrente = 1 if request.form.get('is_recorrente') else 0

        try:
            num_parcelas = int(request.form.get('numero_parcelas', 1))
            valor_total = float(valor_bruto)
            data_base = datetime.strptime(data_str, '%Y-%m-%d')
        except:
            num_parcelas = 1
            valor_total = 0.0
            data_base = datetime.now()

        # Receita é sempre considerada 'paga' (recebida)
        pago = 1 if tipo == 'receita' or request.form.get('pago') else 0
            
        try:
            # 1. PARCELAMENTO (Cartão)
            if tipo == 'despesa' and metodo == 'Cartão de Crédito' and num_parcelas > 1 and not is_recorrente:
                valor_parcela_base = round(valor_total / num_parcelas, 2)
                diferenca = round(valor_total - (valor_parcela_base * num_parcelas), 2)
                
                id_pai = None
                for i in range(1, num_parcelas + 1):
                    valor_atual = round(valor_parcela_base + diferenca, 2) if i == num_parcelas else valor_parcela_base
                    data_parcela = (data_base + relativedelta(months=i-1)).strftime('%Y-%m-%d')
                    desc_parcela = f"{descricao} ({i}/{num_parcelas})"
                    
                    sql = """INSERT INTO transacoes (usuario_id, descricao, valor_total, tipo, categoria_id, data_transacao, 
                             pago, metodo, id_transacao_pai, parcela_atual, numero_parcelas, is_parcelado, is_recorrente) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, FALSE)"""
                    cursor.execute(sql, (user_id, desc_parcela, valor_atual, tipo, categoria_id, data_parcela, pago, metodo, id_pai, i, num_parcelas))
                    if i == 1:
                        id_pai = cursor.lastrowid
                        cursor.execute("UPDATE transacoes SET id_transacao_pai = %s WHERE id = %s", (id_pai, id_pai))
            
            # 2. RECORRÊNCIA
            elif is_recorrente:
                try:
                    meses_recorrencia = int(request.form.get('meses_recorrencia', 12))
                except:
                    meses_recorrencia = 12

                id_pai = None
                for i in range(meses_recorrencia):
                    data_recorrente = (data_base + relativedelta(months=i)).strftime('%Y-%m-%d')
                    sql = """INSERT INTO transacoes (usuario_id, descricao, valor_total, tipo, categoria_id, data_transacao, 
                             pago, metodo, is_parcelado, is_recorrente, id_transacao_pai) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, TRUE, %s)"""
                    cursor.execute(sql, (user_id, descricao, valor_total, tipo, categoria_id, data_recorrente, pago, metodo, id_pai))
                    if i == 0:
                        id_pai = cursor.lastrowid
                        cursor.execute("UPDATE transacoes SET id_transacao_pai = %s WHERE id = %s", (id_pai, id_pai))

            # 3. ÚNICO
            else:
                sql = """INSERT INTO transacoes (usuario_id, descricao, valor_total, tipo, categoria_id, data_transacao, 
                         pago, metodo, is_parcelado, is_recorrente) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, FALSE)"""
                cursor.execute(sql, (user_id, descricao, valor_total, tipo, categoria_id, data_str, pago, metodo))

            conn.commit()
            flash("Sucesso!", "sucesso")
        except Exception as e:
            conn.rollback()
            flash(f"Erro: {e}", "erro")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('novo_lancamento'))
    
    # GET: Carregar categorias e renderizar
    cursor.execute("SELECT id, nome, tipo FROM categorias WHERE usuario_id = %s ORDER BY nome", (session['usuario_id'],))
    categorias = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('novo_lancamento.html', categorias=categorias, hoje=datetime.now().strftime('%Y-%m-%d'))

# Listagem de Lançamentos
@app.route('/listagem', methods=['GET', 'POST'])
def listagem():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['usuario_id']
    agora = datetime.now()
    hoje = agora.date()
        
    # Pegamos o valor da URL. Se não existir, usamos o mês/ano atual do sistema.
    mes_str = request.args.get('mes_filtro') or agora.strftime('%Y-%m')

    # Agora tentamos transformar em data para os cálculos de navegação
    try:
        data_atual = datetime.strptime(mes_str, '%Y-%m')
    except (ValueError, TypeError):
        # Se o formato vier errado na URL, voltamos para o padrão
        data_atual = agora
        mes_str = agora.strftime('%Y-%m')
    
    # Cálculos para os botões (Usando a data que agora temos certeza que existe)
    mes_anterior = (data_atual - relativedelta(months=1)).strftime('%Y-%m')
    mes_proximo = (data_atual + relativedelta(months=1)).strftime('%Y-%m')
    mes_hoje = agora.strftime('%Y-%m')
    
    # Filtros via URL
    busca = request.args.get('busca', '')
    mes_manual = request.args.get('mes', '')
    ano_filtro = request.args.get('ano', '')
    categoria_id = request.args.get('categoria')
    metodo_filtro = request.args.get('metodo', '')
    status_filtro = request.args.get('status', '')
    filtro_atrasadas = request.args.get('filtro') == 'atrasadas'
    ano, mes = mes_str.split('-')
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
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
            
            # --- LÓGICA DE FILTRAGEM DE DATA (CORRIGIDA) ---
            
            # 1. Se o usuário buscou um texto, não limitamos a data (Busca Global)
            if busca:
                mes_atual_pt = "Resultado da Busca"
            
            # 2. Se houver filtro de Ano Inteiro
            elif ano_filtro:
                query_base += " AND YEAR(t.data_transacao) = %s"
                params.append(ano_filtro)
                mes_atual_pt = f"Ano {ano_filtro}"
            
            # 3. Prioridade: Navegação (Botões) ou Seleção Manual de Mês
            else:
                # Se mes_manual existir (select), ele manda. Se não, o mes_str (botões) manda.
                data_para_filtrar = mes_manual if (mes_manual and '-' in mes_manual) else mes_str
                ano, mes = data_para_filtrar.split('-')
                query_base += " AND YEAR(t.data_transacao) = %s AND MONTH(t.data_transacao) = %s"
                params.extend([ano, mes])
                
                meses_br = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
                            7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
                mes_atual_pt = meses_br.get(int(mes), "Extrato")

        # Filtros Adicionais (Busca, Categoria, Metodo, Status)
                
        if busca:
            query_base += " AND t.descricao LIKE %s"
            params.append(f"%{busca}%")
        if categoria_id:
            query_base += " AND t.categoria_id = %s"
            params.append(categoria_id)
        if metodo_filtro:
            query_base += " AND t.metodo = %s"
            params.append(metodo_filtro)
        if status_filtro:
            query_base += " AND t.pago = %s"
            params.append(status_filtro)

        sql_lista = """
            SELECT t.*, c.nome as categoria_nome, c.cor as categoria_cor,
            CASE WHEN t.tipo = 'receita' THEN 1 WHEN t.tipo = 'despesa' THEN 2 WHEN t.tipo = 'investimento' THEN 3 ELSE 4 END AS ordem_tipo,
            CASE WHEN t.tipo = 'despesa' THEN t.pago ELSE 0 END AS ordem_pagamento
        """ + query_base + """ 
            ORDER BY ordem_tipo ASC, t.data_transacao ASC, ordem_pagamento ASC, categoria_nome ASC, t.descricao ASC
        """
        
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
                           transacoes=transacoes, total_receitas=total_receitas,
                           total_despesas=total_despesas, total_investimentos=total_invest_pagos,
                           saldo_atual=saldo_projetado, total_pago=total_pago,
                           total_pendente=total_pendente, percentual_gasto=percentual_gasto,
                           status_financeiro=status_financeiro, sugestao=sugestao,
                           titulo=titulo_pagina, mes_atual_pt=mes_atual_pt,
                           mes_atual=mes_str, mes_anterior=mes_anterior,
                           mes_proximo=mes_proximo, mes_hoje=mes_hoje,
                           anos=anos_disponiveis, categorias=categorias)

# Excluir Lançamento
@app.route('/excluir_transacao/<int:id>', methods=['POST'])
def excluir_transacao(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['usuario_id']
    tipo_exclusao = request.form.get('tipo_exclusao', 'somente_esta')
    # Captura o mês vindo da URL (?mes_filtro=...)
    mes_retorno = request.args.get('mes_filtro')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Busca os dados da transação antes de deletar
        cursor.execute("SELECT * FROM transacoes WHERE id = %s AND usuario_id = %s", (id, user_id))
        transacao = cursor.fetchone()

        if not transacao:
            flash("Lançamento não encontrado.", "erro")
            return redirect(url_for('listagem', mes_filtro=mes_retorno))

        # 2. Lógica para "Esta e as próximas"
        if tipo_exclusao == 'esta_e_proximas':
            id_pai = transacao['id_transacao_pai'] if transacao['id_transacao_pai'] else transacao['id']
            data_limite = transacao['data_transacao']

            sql = """
                DELETE FROM transacoes 
                WHERE (id_transacao_pai = %s OR id = %s) 
                AND data_transacao >= %s 
                AND usuario_id = %s
            """
            cursor.execute(sql, (id_pai, id_pai, data_limite, user_id))
        
        # 3. Lógica para "Somente esta"
        else:
            sql = "DELETE FROM transacoes WHERE id = %s AND usuario_id = %s"
            cursor.execute(sql, (id, user_id))

        # EFETIVA A EXCLUSÃO NO BANCO
        conn.commit()
        flash("Exclusão realizada com sucesso!", "sucesso")

    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro ao excluir: {e}")
        flash("Erro ao tentar excluir o lançamento.", "erro")
    finally:
        cursor.close()
        conn.close()

    # RETORNO ÚNICO: Redireciona mantendo o mês se ele existir
    return redirect(url_for('listagem', mes_filtro=mes_retorno))

@app.route('/excluir_massa', methods=['POST'])
def excluir_massa():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Pega a lista de IDs vindos dos checkboxes
    ids_para_excluir = request.form.getlist('transacoes_selecionadas')
    user_id = session['usuario_id']
    mes_retorno = request.args.get('mes_filtro') or request.form.get('mes_filtro')
    
    if not ids_para_excluir:
        flash("Nenhuma transação selecionada para exclusão.", "erro")
        return redirect(url_for('listagem'))

    if ids_para_excluir:
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            # Deletamos apenas se pertencerem ao usuário logado (segurança!)
            format_strings = ','.join(['%s'] * len(ids_para_excluir))
            query = f"DELETE FROM transacoes WHERE id IN ({format_strings}) AND usuario_id = %s"
            
            cursor.execute(query, tuple(ids_para_excluir) + (user_id,))
            conn.commit()
            
            flash(f"{len(ids_para_excluir)} transações excluídas com sucesso!", "sucesso")
        except Exception as e:
            flash(f"Erro ao excluir transações: {str(e)}", "erro")
        finally:
            cursor.close()
            conn.close()
    else:
        flash("Nenhuma transação selecionada.", "alerta")

    return redirect(url_for('listagem', mes_filtro=mes_retorno))

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

    user_id = session['usuario_id'] # Captura o ID do usuário logado
    mes_da_url = request.args.get('mes_filtro')
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # 1. Busca a transação específica com segurança
    cursor.execute("SELECT * FROM transacoes WHERE id = %s AND usuario_id = %s", (id, user_id))
    transacao = cursor.fetchone()
    
    # 2. Busca categorias APENAS deste usuário para evitar duplicatas de outros usuários
    # Usamos DISTINCT para garantir que nomes iguais no mesmo tipo não apareçam duas vezes
    sql_categorias = """
        SELECT MIN(id) as id, nome, tipo 
        FROM categorias 
        WHERE usuario_id = %s 
        GROUP BY nome, tipo 
        ORDER BY nome
    """
    cursor.execute(sql_categorias, (user_id,))
    categorias = cursor.fetchall()
    
    cursor.close()
    conn.close()

    if not transacao:
        flash("Transação não encontrada ou acesso negado.", "erro")
        return redirect(url_for('listagem'))

    return render_template('editar_transacao.html', transacao=transacao, categorias=categorias, mes_filtro=mes_da_url)

# ROTA ÚNICA PARA PROCESSAR A ATUALIZAÇÃO (POST)
@app.route('/atualizar_transacao/<int:id>', methods=['POST'])
def atualizar_transacao(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    user_id = session['usuario_id']
    mes_retorno = request.form.get('mes_filtro_retorno')
    
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

    # --- DEBUGER/CORREÇÃO: Regra de Negócio para Tipo de Lançamento ---
    if tipo == 'receita':
        pago = 1
        novo_metodo = "Entrada" # Receitas geralmente não variam o método na edição simples
    elif tipo == 'investimento':
        # Investimentos seguem a lógica de "Aporte realizado" (checkbox pago)
        pago = 1 if request.form.get('pago') else 0
        novo_metodo = request.form.get('metodo') or 'Transferência'
    else: # Despesa
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
            return redirect(url_for('listagem', mes_filtro=mes_retorno))

        # --- LÓGICA DE ATUALIZAÇÃO RECORRENTE (ESTA E PRÓXIMAS) ---
        if tipo_edicao == 'recorrente_futuras' and original['is_recorrente']:
            id_pai = original['id_transacao_pai'] if original['id_transacao_pai'] else original['id']
            data_original = original['data_transacao']

            sql_recorrente = """
                UPDATE transacoes 
                SET descricao = %s, valor_total = %s, categoria_id = %s, 
                    metodo = %s, tipo = %s, pago = %s
                WHERE (id_transacao_pai = %s OR id = %s) 
                AND data_transacao >= %s 
                AND usuario_id = %s
            """
            cursor.execute(sql_recorrente, (nova_descricao, novo_valor_total, nova_categoria, 
                                            novo_metodo, tipo, pago, id_pai, id_pai, data_original, user_id))

        # --- LÓGICA DE ATUALIZAÇÃO EM GRUPO (PARCELAS) ---
        elif tipo_edicao == 'grupo' and original['is_parcelado']:
            id_pai = original['id_transacao_pai'] if original['id_transacao_pai'] else original['id']
            novo_total_p = int(request.form.get('novo_total_parcelas', original['numero_parcelas']))
            nome_limpo = nova_descricao.split(' (')[0].strip()

            valor_parcela_base = round(novo_valor_total / novo_total_p, 2)
            diferenca = round(novo_valor_total - (valor_parcela_base * novo_total_p), 2)

            cursor.execute("SELECT id, parcela_atual FROM transacoes WHERE (id = %s OR id_transacao_pai = %s) AND usuario_id = %s", (id_pai, id_pai, user_id))
            parcelas_do_grupo = cursor.fetchall()

            for parcela in parcelas_do_grupo:
                valor_final_parcela = round(valor_parcela_base + diferenca, 2) if parcela['parcela_atual'] == novo_total_p else valor_parcela_base
                desc_formatada = f"{nome_limpo} ({parcela['parcela_atual']}/{novo_total_p})"
                
                sql_grupo = """
                    UPDATE transacoes SET descricao = %s, valor_total = %s, categoria_id = %s, 
                    metodo = %s, tipo = %s, pago = %s, numero_parcelas = %s WHERE id = %s
                """
                cursor.execute(sql_grupo, (desc_formatada, valor_final_parcela, nova_categoria, 
                                           novo_metodo, tipo, pago, novo_total_p, parcela['id']))

        # --- LÓGICA DE ATUALIZAÇÃO INDIVIDUAL (Funciona para todos, incluindo Investimento único) ---
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

    return redirect(url_for('listagem', mes_filtro=mes_retorno))

# Alternar Status de Pagamento
@app.route('/alternar_pagamento/<int:id>', methods=['POST'])
def alternar_pagamento(id):
    if 'usuario_id' not in session:
        return jsonify({'status': 'erro', 'mensagem': 'Não logado'}), 401
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Busca a transação
        cursor.execute("SELECT pago, tipo, data_transacao FROM transacoes WHERE id = %s", (id,))
        resultado = cursor.fetchone()
        
        if resultado:
            pago_atual = resultado['pago']
            tipo = resultado['tipo'].strip().lower()
            data_referencia = resultado['data_transacao']

            # Alterna o status
            novo_status = 1 if tipo == 'receita' else (0 if pago_atual == 1 else 1)
            cursor.execute("UPDATE transacoes SET pago = %s WHERE id = %s", (novo_status, id))
            conn.commit()

            # Busca transações do mês para recalcular o painel
            cursor.execute("""
                SELECT tipo, pago, valor_total 
                FROM transacoes 
                WHERE usuario_id = %s 
                AND MONTH(data_transacao) = %s 
                AND YEAR(data_transacao) = %s
            """, (session['usuario_id'], data_referencia.month, data_referencia.year))
            
            transacoes_mes = cursor.fetchall()
            
            # Cálculos matemáticos
            total_receitas = sum(float(t['valor_total']) for t in transacoes_mes if t['tipo'].lower() == 'receita')
            total_investimentos = sum(float(t['valor_total']) for t in transacoes_mes if t['tipo'].lower() == 'investimento' and t['pago'] == 1)
            total_despesas = sum(float(t['valor_total']) for t in transacoes_mes if t['tipo'].lower() == 'despesa')
            
            saldo_projetado = total_receitas - total_despesas - total_investimentos
            total_pago = sum(float(t['valor_total']) for t in transacoes_mes if t['pago'] == 1 and t['tipo'].lower() == 'despesa')
            total_pendente = sum(float(t['valor_total']) for t in transacoes_mes if t['pago'] == 0 and t['tipo'].lower() == 'despesa')
            percentual_gasto = (total_despesas / total_receitas * 100) if total_receitas > 0 else 0

            # Diagnóstico Financeiro
            if saldo_projetado < 0:
                status_f = "Crítico"
                sugest = "Suas saídas superaram as entradas. Revise seus custos urgentemente."
            elif percentual_gasto > 80:
                status_f = "Atenção"
                sugest = "Você já comprometeu mais de 80% da sua receita."
            else:
                status_f = "Saudável"
                sugest = "Seu orçamento está equilibrado."

            # RESPOSTA PARA AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'status': 'sucesso',
                    'novo_receita': total_receitas,
                    'novo_despesa': total_despesas,
                    'novo_saldo': saldo_projetado,
                    'novo_pago': total_pago,
                    'novo_pendente': total_pendente,
                    'novo_aporte': total_investimentos,
                    'status_financeiro': status_f,
                    'sugestao': sugest,
                    'percentual_gasto': percentual_gasto
                })

        # RESPOSTA PARA CLIQUE NORMAL (RECARGA DE PÁGINA)
        return redirect(request.referrer or url_for('listagem'))

    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

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

@app.route('/exportar_excel')
def exportar_excel():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    user_id = session['usuario_id']
    mes_filtro = request.args.get('mes_filtro', '')
    ano_filtro = request.args.get('ano_filtro', '')
    busca = request.args.get('busca', '')

    if not any([mes_filtro, ano_filtro, busca]):
        mes_filtro = datetime.now().strftime('%Y-%m')

    nome_arquivo = f"Extrato_{mes_filtro}.xlsx" if mes_filtro else "Extrato_Geral.xlsx"

    query = """
        SELECT t.data_transacao, t.tipo, c.nome as categoria_nome, c.cor as categoria_cor, 
        t.descricao, t.valor_total, t.pago
        FROM transacoes t 
        LEFT JOIN categorias c ON t.categoria_id = c.id
        WHERE t.usuario_id = %s
    """
    params = [user_id]
    if mes_filtro:
        ano, mes = mes_filtro.split('-')
        query += " AND YEAR(data_transacao) = %s AND MONTH(data_transacao) = %s"
        params.extend([ano, mes])
    
    query += " ORDER BY t.data_transacao ASC"
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, tuple(params))
    dados_brutos = cursor.fetchall()
    cursor.close()
    conn.close()

    if not dados_brutos:
        return "<script>alert('Sem dados.'); window.history.back();</script>"

    df = pd.DataFrame(dados_brutos)
    df['data_transacao'] = pd.to_datetime(df['data_transacao'], errors='coerce').dt.tz_localize(None)
    df['status'] = df['pago'].map({1: 'PAGO', 0: 'PENDENTE'})
    df['valor_total'] = pd.to_numeric(df['valor_total'], errors='coerce').fillna(0)
    
    df_final = df[['data_transacao', 'tipo', 'categoria_nome', 'descricao', 'valor_total', 'status']]
    # Agrupamento para o resumo lateral
    df_cat = df[df['tipo'] == 'despesa'].groupby(['categoria_nome', 'categoria_cor'])['valor_total'].sum().reset_index()
    df_cat = df_cat.sort_values(by='valor_total', ascending=False)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter', datetime_format='dd/mm/yyyy') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Extrato', startrow=1, header=False)
        workbook = writer.book
        worksheet = writer.sheets['Extrato']

        # --- DEFINIÇÃO DE FORMATOS (TODOS AQUI) ---
        fmt_moeda = workbook.add_format({'num_format': 'R$ #,##0.00', 'align': 'left', 'border': 1})
        fmt_data = workbook.add_format({'num_format': 'dd/mm/yyyy', 'align': 'left', 'border': 1})
        fmt_texto = workbook.add_format({'align': 'left', 'border': 1})
        fmt_pago = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100', 'bold': True, 'border': 1, 'num_format': 'R$ #,##0.00', 'align': 'left'})
        fmt_pendente = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'bold': True, 'border': 1, 'num_format': 'R$ #,##0.00', 'align': 'left'})
        fmt_header = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'align': 'left'})
        fmt_saldo_positivo = workbook.add_format({
            'bold': True, 'bg_color': '#C6EFCE', 'font_color': '#006100', 
            'border': 1, 'num_format': 'R$ #,##0.00', 'align': 'left'
        })
        fmt_saldo_negativo = workbook.add_format({
            'bold': True, 'bg_color': '#FFC7CE', 'font_color': '#9C0006', 
            'border': 1, 'num_format': 'R$ #,##0.00', 'align': 'left'
        })
        # --- TABELA PRINCIPAL ---
        (max_row, max_col) = df_final.shape
        worksheet.add_table(0, 0, max_row, max_col - 1, {
            'columns': [{'header': 'DATA'}, {'header': 'TIPO'}, {'header': 'CATEGORIA'}, 
                        {'header': 'DESCRIÇÃO'}, {'header': 'VALOR'}, {'header': 'STATUS'}],
            'style': 'Table Style Medium 2'
        })

        # --- LOOP PARA APLICAR FORMATOS E CORES (EVITA BORDAS NAS CÉLULAS VAZIAS) ---
        for row_num in range(1, max_row + 1):
            ln = df.iloc[row_num-1]
            worksheet.write(row_num, 0, ln['data_transacao'], fmt_data)
            worksheet.write(row_num, 1, ln['tipo'], fmt_texto)
            
            # Categoria com cor
            cor = ln['categoria_cor']
            fmt_cat_cor = workbook.add_format({'bg_color': cor or '#FFFFFF', 'font_color': '#FFFFFF' if cor else '#000000', 'bold': True, 'border': 1, 'align': 'left'})
            worksheet.write(row_num, 2, ln['categoria_nome'], fmt_cat_cor)
            
            worksheet.write(row_num, 3, ln['descricao'], fmt_texto)
            worksheet.write(row_num, 4, float(ln['valor_total']), fmt_moeda) # FORÇA R$ E ALINHAMENTO
            
            # Status
            st_fmt = fmt_pago if ln['pago'] == 1 else fmt_pendente
            worksheet.write(row_num, 5, ln['status'], st_fmt)

        # Ajuste de largura das colunas
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:D', 25)
        worksheet.set_column('E:E', 20)
        worksheet.set_column('F:F', 15)

        # --- RESUMO POR CATEGORIA (LADO DIREITO) ---
        col_res = 8
        worksheet.write(0, col_res, 'RESUMO POR CATEGORIA', fmt_header)
        worksheet.write(0, col_res + 1, 'VALOR GASTO', fmt_header)
        worksheet.set_column(col_res, col_res, 35)
        worksheet.set_column(col_res + 1, col_res + 1, 20)

        for i, row in enumerate(df_cat.itertuples(), start=1):
            fmt_res_cor = workbook.add_format({'bg_color': row.categoria_cor, 'font_color': '#FFFFFF', 'bold': True, 'border': 1, 'align': 'left'})
            worksheet.write(i, col_res, row.categoria_nome, fmt_res_cor)
            worksheet.write(i, col_res + 1, float(row.valor_total), fmt_moeda)

        # --- TOTAIS FINAIS ---
        receitas = df[df['tipo'] == 'receita']['valor_total'].sum()
        despesas = df[df['tipo'] == 'despesa']['valor_total'].sum()
        pagas = df[(df['tipo'] == 'despesa') & (df['pago'] == 1)]['valor_total'].sum()
        pendentes = df[(df['tipo'] == 'despesa') & (df['pago'] == 0)]['valor_total'].sum()
        saldo = receitas - despesas

        res_row = max_row + 3
        worksheet.write(res_row, 3, 'TOTAL RECEITAS:', fmt_header)
        worksheet.write(res_row, 4, receitas, fmt_moeda)
        worksheet.write(res_row + 1, 3, 'TOTAL DESPESAS:', fmt_header)
        worksheet.write(res_row + 1, 4, despesas, fmt_moeda)
        worksheet.write(res_row + 2, 3, '(-) JÁ PAGO:', fmt_header)
        worksheet.write(res_row + 2, 4, pagas, fmt_pago)
        worksheet.write(res_row + 3, 3, '(=) PENDENTE:', fmt_header)
        worksheet.write(res_row + 3, 4, pendentes, fmt_pendente)
        worksheet.write(res_row + 5, 3, 'SALDO PROJETADO:', fmt_header)
        if saldo >= 0:
            worksheet.write(res_row + 5, 4, saldo, fmt_saldo_positivo)
        else:
            worksheet.write(res_row + 5, 4, saldo, fmt_saldo_negativo)

    output.seek(0)
    return send_file(output, as_attachment=True, download_name=nome_arquivo)

# # Dicionário de Inteligência - Adicione aqui novos termos conforme precisar
# REGRAS_INTELIGENCIA = {
#     'IFOOD': 'Alimentação',
#     'BURGER KING': 'Alimentação',
#     'SUBWAY': 'Alimentação',
#     'PADARIA': 'Alimentação',
#     'RESTAURANTE': 'Alimentação',
#     'UBER': 'Transporte',
#     '99APP': 'Transporte',
#     'CMA PROTECAO': 'Transporte',
#     'NETFLIX': 'Lazer',
#     'SPOTIFY': 'Lazer',
#     'SHELL': 'Combustível',
#     'IPIRANGA': 'Combustível',
#     'POSTO': 'Combustível',
#     'MERCADO': 'Supermercado',
#     'SUPERMERCADO': 'Supermercado',
#     'EPA': 'Supermercado',
#     'DMA': 'Supermercado',
#     'CONDOMINIO': 'Moradia',
#     'DROG ARAUJO': 'Saúde',
#     'FARMACIA': 'Saúde',
#     'DROGARIA ': 'Saúde',
#     'COPASA': 'Contas Fixas',
#     'CEMIG': 'Contas Fixas',
#     'VIVO': 'Contas Fixas',
#     'TIM': 'Contas Fixas',
#     'DENTAL BH B': 'Salário'
# }

def descobrir_categoria_por_inteligencia(descricao, usuario_id, cursor, conn, tipo_transacao):
    """
    Busca nas regras do banco se a descrição dá match com algum termo.
    Se der match e a categoria não existir, ela é criada na hora.
    """
    descricao_upper = descricao.upper()
    
    # 1. Busca as regras dinâmicas do banco de dados
    cursor.execute("SELECT termo, categoria_nome FROM inteligencia_regras WHERE usuario_id = %s", (usuario_id,))
    regras = cursor.fetchall()

    for regra in regras:
        termo_regra = regra['termo'].upper()
        if termo_regra in descricao_upper:
            nome_cat_alvo = regra['categoria_nome']
            
            # 2. Verifica se o usuário já tem essa categoria cadastrada
            cursor.execute("SELECT id FROM categorias WHERE nome = %s AND usuario_id = %s", (nome_cat_alvo, usuario_id))
            res_cat = cursor.fetchone()
            
            if res_cat:
                return res_cat['id']
            else:
                # 3. AUTO-CADASTRO: Se a regra existe mas a categoria não, cria agora
                cursor.execute(
                    "INSERT INTO categorias (nome, tipo, usuario_id, cor) VALUES (%s, %s, %s, %s)",
                    (nome_cat_alvo, tipo_transacao, usuario_id, '#6c757d')
                )
                conn.commit() # Commit para garantir que o ID exista para as próximas transações
                return cursor.lastrowid
                
    return None

@app.route('/importar_ofx', methods=['POST'])
@login_required
def importar_ofx():
    file = request.files.get('arquivo_ofx')
    if not file or file.filename == '':
        flash("Selecione um arquivo OFX válido.", "erro")
        return redirect(url_for('listagem'))

    user_id = session['usuario_id']
    
    try:
        # --- LIMPEZA E PARSE DO ARQUIVO ---
        raw_content = file.read().decode('iso-8859-1')
        def substituir_fitid_vazio(match):
            return f"<FITID>{uuid.uuid4().hex}"
        content_fixed = re.sub(r'<FITID>\s*(\r?\n|<)', substituir_fitid_vazio, raw_content)
        content_fixed = content_fixed.replace('<FITID></FITID>', f'<FITID>{uuid.uuid4().hex}</FITID>')

        ofx_file = StringIO(content_fixed)
        ofx = OfxParser.parse(ofx_file)

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # --- CATEGORIA PADRÃO (Caso a inteligência não encontre nada) ---
        cursor.execute("SELECT id FROM categorias WHERE nome = 'Importado' AND usuario_id = %s", (user_id,))
        cat_res = cursor.fetchone()
        id_categoria_padrao = cat_res['id'] if cat_res else None

        if not id_categoria_padrao:
            cursor.execute("INSERT INTO categorias (nome, tipo, usuario_id, cor) VALUES (%s, %s, %s, %s)", 
                           ('Importado', 'despesa', user_id, '#6c757d'))
            conn.commit()
            id_categoria_padrao = cursor.lastrowid

        # --- PROCESSAMENTO ---
        importados_ids = []
        contador_inteligencia = 0

        for account in ofx.accounts:
            for tx in account.statement.transactions:
                valor = float(tx.amount)
                tipo = 'receita' if valor > 0 else 'despesa'
                valor_abs = abs(valor)
                data_tx = tx.date.strftime('%Y-%m-%d')
                descricao = (tx.memo or tx.payee or "Transação OFX").strip()

                # --- CHAMADA DA INTELIGÊNCIA ---
                id_final = descobrir_categoria_por_inteligencia(descricao, user_id, cursor, conn, tipo)
                
                if id_final:
                    contador_inteligencia += 1
                else:
                    id_final = id_categoria_padrao

                # --- VERIFICA DUPLICIDADE ---
                cursor.execute("""
                    SELECT id FROM transacoes 
                    WHERE usuario_id = %s AND valor_total = %s 
                    AND data_transacao = %s AND descricao = %s
                """, (user_id, valor_abs, data_tx, descricao))
                
                if not cursor.fetchone():
                    sql = """INSERT INTO transacoes (usuario_id, descricao, valor_total, tipo, 
                             categoria_id, data_transacao, pago, metodo)
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                    cursor.execute(sql, (user_id, descricao, valor_abs, tipo, 
                                         id_final, data_tx, 1, 'OFX'))
                    importados_ids.append(str(cursor.lastrowid))

        conn.commit()
        cursor.close()
        conn.close()

        if importados_ids:
            msg = f"Sucesso! {len(importados_ids)} transações importadas."
            if contador_inteligencia > 0:
                msg += f" Sendo {contador_inteligencia} classificadas pela inteligência."
            flash(msg, "sucesso")
            return redirect(url_for('listagem', auto_select=",".join(importados_ids)))
        else:
            flash("Nenhuma transação nova encontrada no arquivo.", "info")
            return redirect(url_for('listagem'))

    except Exception as e:
        flash(f"Erro ao importar OFX: {str(e)}", "erro")
        return redirect(url_for('listagem'))

def obter_ou_criar_categoria(nome_categoria, usuario_id, cursor, conn):
    # 1. Busca se a categoria já existe para o usuário
    cursor.execute("SELECT id FROM categorias WHERE nome = %s AND usuario_id = %s", (nome_categoria, usuario_id))
    cat = cursor.fetchone()
    
    if cat:
        return cat['id']
    else:
        # 2. Se não existir, cadastra automaticamente (com uma cor padrão)
        cursor.execute(
            "INSERT INTO categorias (nome, usuario_id, cor) VALUES (%s, %s, %s)",
            (nome_categoria, usuario_id, "#6c757d") # Cinza padrão
        )
        conn.commit()
        return cursor.lastrowid

def aplicar_inteligencia(descricao, usuario_id, cursor, conn):
    descricao_upper = descricao.upper()
    
    # Busca as regras no banco (Dicionário dinâmico)
    cursor.execute("SELECT termo, categoria_nome FROM inteligencia_regras WHERE usuario_id = %s", (usuario_id,))
    regras = cursor.fetchall()

    for regra in regras:
        if regra['termo'] in descricao_upper:
            # Encontrou um termo! Agora garante que a categoria existe
            return obter_ou_criar_categoria(regra['categoria_nome'], usuario_id, cursor, conn)
    
    return None # Nenhuma regra encontrada

@app.route('/configuracoes/inteligencia')
@login_required
def inteligencia_index():
    user_id = session.get('usuario_id')
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # Busca as regras vinculando com a tabela de categorias para pegar TIPO e COR
    query = """
        SELECT r.*, c.tipo, c.cor, c.id as categoria_id
        FROM inteligencia_regras r
        LEFT JOIN categorias c ON r.categoria_nome = c.nome AND r.usuario_id = c.usuario_id
        WHERE r.usuario_id = %s
        ORDER BY r.termo
    """
    cursor.execute(query, [user_id])
    regras = cursor.fetchall()
    
    # Busca categorias para o select do formulário
    cursor.execute("SELECT * FROM categorias WHERE usuario_id = %s ORDER BY nome", [user_id])
    categorias = cursor.fetchall()
    
    conn.close()
    return render_template('inteligencia.html', regras=regras, categorias=categorias)

@app.route('/salvar_regra', methods=['POST'])
@login_required
def salvar_regra():
    user_id = session.get('usuario_id')
    termo = request.form.get('termo').upper().strip()
    categoria_id = request.form.get('categoria_id')
    
    # Campos da nova categoria
    nova_cat_nome = request.form.get('nova_categoria_nome')
    nova_cat_tipo = request.form.get('nova_categoria_tipo') # <--- Verifique se este nome bate com o HTML
    nova_cat_cor = request.form.get('cor', '#6c757d')

    # DEBUG: Veja no terminal se o 'investimento' está chegando aqui
    print(f"DEBUG: Termo: {termo}, Tipo: {nova_cat_tipo}")

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    try:
        if categoria_id == 'nova':
            # Verifique se o INSERT está incluindo o tipo
            sql_cat = "INSERT INTO categorias (nome, tipo, usuario_id, cor) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql_cat, (nova_cat_nome, nova_cat_tipo, user_id, nova_cat_cor))
            
            id_final_categoria = cursor.lastrowid
            nome_final_categoria = nova_cat_nome
        else:
            # Se for categoria existente, buscamos os dados dela
            cursor.execute("SELECT id, nome FROM categorias WHERE id = %s", [categoria_id])
            res = cursor.fetchone()
            id_final_categoria = res['id']
            nome_final_categoria = res['nome']

        # Salva a regra de inteligência
        cursor.execute(
            "INSERT INTO inteligencia_regras (usuario_id, termo, categoria_nome) VALUES (%s, %s, %s)",
            (user_id, termo, nome_final_categoria)
        )

        conn.commit() # <--- ESSENCIAL PARA SALVAR NO BANCO
        flash("Regra e Categoria salvas com sucesso!", "sucesso")
        
    except Exception as e:
        conn.rollback()
        print(f"ERRO AO SALVAR: {e}")
        flash(f"Erro ao salvar: {e}", "erro")
    finally:
        conn.close()

    return redirect(url_for('inteligencia_index'))

@app.route('/editar_regra/<int:id>', methods=['POST'])
@login_required
def editar_regra(id):
    user_id = session.get('usuario_id')
    termo_novo = request.form.get('termo').upper().strip()
    cat_nome_nova = request.form.get('categoria_nome').strip()
    tipo_novo = request.form.get('tipo')
    cor_nova = request.form.get('cor')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Busca o nome antigo da categoria para poder renomeá-la se necessário
        cursor.execute("SELECT categoria_nome FROM inteligencia_regras WHERE id = %s", [id])
        regra_antiga = cursor.fetchone()
        nome_antigo = regra_antiga['categoria_nome']

        # 2. Atualiza a categoria vinculada (Nome, Tipo e Cor)
        cursor.execute("""
            UPDATE categorias 
            SET nome = %s, tipo = %s, cor = %s 
            WHERE nome = %s AND usuario_id = %s
        """, (cat_nome_nova, tipo_novo, cor_nova, nome_antigo, user_id))

        # 3. Atualiza o termo e o nome da categoria na regra de inteligência
        cursor.execute("""
            UPDATE inteligencia_regras 
            SET termo = %s, categoria_nome = %s 
            WHERE id = %s
        """, (termo_novo, cat_nome_nova, id))

        conn.commit()
        flash("Alterações salvas com sucesso!", "sucesso")
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao atualizar: {e}", "erro")
    finally:
        conn.close()

    return redirect(url_for('inteligencia_index'))

@app.route('/excluir_regra/<int:id>', methods=['POST'])
@login_required
def excluir_regra(id):
    user_id = session.get('usuario_id')
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # Garante que a regra pertence ao utilizador logado antes de apagar
    cursor.execute("DELETE FROM inteligencia_regras WHERE id = %s AND usuario_id = %s", (id, user_id))
    
    conn.commit()
    conn.close()
    flash("Regra de inteligência removida.", "info")
    return redirect(url_for('inteligencia_index'))

def obter_progresso_metas(user_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # Busca as metas e soma os gastos do mês atual para cada categoria com meta
    query = """
        SELECT 
            m.valor_limite, 
            c.nome AS categoria_nome,
            (SELECT SUM(valor_total) FROM transacoes 
             WHERE categoria_id = m.categoria_id 
             AND usuario_id = %s 
             AND tipo = 'despesa'
             AND MONTH(data_transacao) = MONTH(CURRENT_DATE())
             AND YEAR(data_transacao) = YEAR(CURRENT_DATE())
            ) AS total_gasto
        FROM metas m
        JOIN categorias c ON m.categoria_id = c.id
        WHERE m.usuario_id = %s
    """
    cursor.execute(query, (user_id, user_id))
    metas = cursor.fetchall()
    
    # Processa percentuais e cores
    for meta in metas:
        gasto = meta['total_gasto'] or 0
        limite = meta['valor_limite']
        percentual = min((gasto / limite) * 100, 100) # trava em 100% para a barra não quebrar
        
        meta['percentual'] = percentual
        # Lógica de cor: verde < 70%, amarela < 90%, vermelha >= 90%
        if percentual < 70: meta['cor_barra'] = 'bg-success'
        elif percentual < 90: meta['cor_barra'] = 'bg-warning'
        else: meta['cor_barra'] = 'bg-danger'
        
    cursor.close()
    conn.close()
    return metas

@app.route('/configurar_metas', methods=['GET', 'POST'])
def configurar_metas():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['usuario_id']
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Recebe os dicionários do formulário: {categoria_id: valor_limite}
        metas_input = request.form.to_dict()
        
        try:
            for cat_id, valor in metas_input.items():
                if valor and float(valor) > 0:
                    # Lógica de "UPSERT": Se já existe meta para esta categoria, atualiza. Se não, insere.
                    query = """
                        INSERT INTO metas (usuario_id, categoria_id, valor_limite)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE valor_limite = VALUES(valor_limite)
                    """
                    cursor.execute(query, (user_id, cat_id, float(valor)))
            
            conn.commit()
            flash("Metas atualizadas com sucesso!", "sucesso")
        except Exception as e:
            flash(f"Erro ao salvar metas: {str(e)}", "erro")
        
        return redirect(url_for('index'))

    # GET: Busca categorias e os valores das metas já salvos
    # --- 1. BUSCA RECEITA TOTAL DO MÊS ---
    query_receita = """
        SELECT SUM(valor_total) as total 
        FROM transacoes 
        WHERE usuario_id = %s 
        AND tipo = 'receita' 
        AND MONTH(data_transacao) = MONTH(CURRENT_DATE()) 
        AND YEAR(data_transacao) = YEAR(CURRENT_DATE())
    """
   
    cursor.execute(query_receita, (user_id,))
    resultado_receita = cursor.fetchone()
    total_receitas = resultado_receita['total'] if resultado_receita['total'] else 0

    # --- 2. BUSCA CATEGORIAS E METAS (Importante para a tabela aparecer!) ---
    query_metas = """
        SELECT c.id, c.nome, c.tipo, c.cor, m.valor_limite 
        FROM categorias c
        LEFT JOIN metas m ON c.id = m.categoria_id AND m.usuario_id = %s
        WHERE c.usuario_id = %s
    """
    cursor.execute(query_metas, (user_id, user_id))
    categorias_metas = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template('metas.html',
                           categorias=categorias_metas,
                           receita_total=total_receitas)

@app.route('/api/simular', methods=['POST'])
def api_simular():
    try:
        dados = request.json
        valor_da_compra = float(dados.get('valor', 0))
        num_parcelas = int(dados.get('parcelas', 1))
        valor_parcela = valor_da_compra / num_parcelas
        
        resultados = []
        hoje = datetime.now()
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        for i in range(6):
            data_analise = hoje + relativedelta(months=i)
            mes = data_analise.month
            ano = data_analise.year

            # QUERY FINAL: Usando 'valor_total' e 'data_transacao'
            query = """
                SELECT 
                    SUM(CASE WHEN tipo = 'Receita' THEN valor_total ELSE 0 END) as total_receita,
                    SUM(CASE WHEN tipo = 'Despesa' THEN valor_total ELSE 0 END) as total_despesa
                FROM transacoes 
                WHERE MONTH(data_transacao) = %s AND YEAR(data_transacao) = %s
            """
            cursor.execute(query, (mes, ano))
            res = cursor.fetchone()
            
            receita = float(res['total_receita'] or 0)
            despesa = float(res['total_despesa'] or 0)
            saldo_previsto = receita - despesa
            
            resultados.append({
                'mes_nome': data_analise.strftime('%b/%y'),
                'saldo_previsto': saldo_previsto,
                'cabe': (saldo_previsto >= valor_parcela)
            })

        cursor.close()
        conn.close()

        melhor_opcao = max(resultados, key=lambda x: x['saldo_previsto'])
        status_geral = "positivo" if melhor_opcao['saldo_previsto'] > 0 else "alerta"
        
        return jsonify({
            'analise': resultados,
            'melhor_mes': melhor_opcao['mes_nome'],
            'maior_folga': melhor_opcao['saldo_previsto'],
            'valor_parcela': valor_parcela,
            'status_geral': status_geral
        })

    except Exception as e:
        print(f"Erro no Simulador: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route('/ajuda')
def ajuda():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('ajuda.html')

@app.route('/testar-meu-push')
def testar_meu_push():
    if 'usuario_id' not in session:
        return "Erro: Você precisa estar logado no sistema para testar."

    user_id = session['usuario_id']
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # 1. Busca todos os dispositivos DO SEU USUÁRIO
        cursor.execute("SELECT subscription_json, nome_dispositivo FROM inscricoes_push WHERE usuario_id = %s", (user_id,))
        dispositivos = cursor.fetchall()

        if not dispositivos:
            return "Nenhum dispositivo cadastrado para este usuário!"

        # 2. Prepara a mensagem
        payload = {
            "title": "Teste MyFinance",
            "body": "Alerta de teste funcionando",
            "url": "/"
        }

        enviados = 0
        erros = 0

        for disp in dispositivos:
            try:
                webpush(
                    subscription_info=json.loads(disp['subscription_json']),
                    data=json.dumps(payload),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": "mailto:bcm.marra@gmail.com"},
                    content_encoding="aes128gcm" # ESSA LINHA É OBRIGATÓRIA PARA NAVEGADORES MODERNOS
                )
                enviados += 1
            except WebPushException as ex:
                # Se falhar, o ex.response.text pode nos dizer o que a Microsoft respondeu
                print(f"Erro detalhado da Microsoft: {ex.response.text}")
                erros += 1

        return f"<h1>Teste Concluído!</h1><p>Enviados: {enviados}</p><p>Falhas: {erros}</p>"

    except Exception as e:
        return f"Erro no servidor: {e}"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/testar-dispositivo/<int:id>')
def testar_dispositivo(id):
    if 'usuario_id' not in session:
        return jsonify({"erro": "Não autorizado"}), 401

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # Busca o dispositivo específico, garantindo que pertença ao usuário logado
    cursor.execute("""
        SELECT subscription_json, nome_dispositivo 
        FROM inscricoes_push 
        WHERE id = %s AND usuario_id = %s
    """, (id, session['usuario_id']))
    
    disp = cursor.fetchone()
    
    if not disp:
        return jsonify({"erro": "Dispositivo não encontrado"}), 404

    try:
        payload = {
            "title": "Teste de Conexão 💡",
            "body": f"O dispositivo '{disp['nome_dispositivo']}' está recebendo alertas corretamente!",
            "url": "/perfil"
        }
        
        webpush(
            subscription_info=json.loads(disp['subscription_json']),
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": "mailto:bcm.marra@gmail.com"},
            content_encoding="aes128gcm",
            headers={
                "Urgency": "high",
                "TTL": "60"
            }
        )
        print("Enviando para o Edge...")
        return jsonify({"sucesso": True})
    
    except WebPushException as ex:
        # Forçamos o print de qualquer detalhe para o seu terminal
        print("--------------------------")
        print(f"ERRO NO PUSH: {ex}")
        if ex.response:
            print(f"RESPOSTA DO SERVIDOR: {ex.response.status_code} - {ex.response.text}")
        print("--------------------------")
        return jsonify({"erro": "Falha no servidor de push"}), 500
    except Exception as e:
        print(f"ERRO GERAL NO PYTHON: {str(e)}")
        return jsonify({"erro": str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()






if __name__ == '__main__':
    app.run(debug=True)