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
    
    mes_atual = int(request.args.get('mes', hoje.month))
    ano_atual = int(request.args.get('ano', hoje.year))
    data_foco = datetime(ano_atual, mes_atual, 1)
    
    # REMOVIDAS as 3 linhas que causavam erro (total_geral, total_pago, total_pendente baseadas em 'transacoes')
    # Agora calcularemos elas abaixo via SQL para serem precisas.

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
        params_mes = (user_id, mes_atual, ano_atual)
        sql_base_mes = "FROM transacoes WHERE usuario_id = %s AND MONTH(data_transacao) = %s AND YEAR(data_transacao) = %s"

        # 1. GASTO TOTAL (Despesas)
        cursor.execute(f"SELECT SUM(valor_total) as total {sql_base_mes} AND tipo = 'despesa'", params_mes)
        res = cursor.fetchone()
        gasto_mes = float(res['total']) if res and res['total'] else 0.0
        total_geral = gasto_mes # Para manter compatibilidade com seu HTML

        # 2. TOTAL PAGO
        cursor.execute(f"SELECT SUM(valor_total) as total {sql_base_mes} AND pago = 1 AND tipo = 'despesa'", params_mes)
        res = cursor.fetchone()
        total_pago = float(res['total']) if res and res['total'] else 0.0

        # 3. TOTAL PENDENTE
        cursor.execute(f"SELECT SUM(valor_total) as total {sql_base_mes} AND pago = 0 AND tipo = 'despesa'", params_mes)
        res = cursor.fetchone()
        total_pendente = float(res['total']) if res and res['total'] else 0.0

        # --- NOVOS COMANDOS PARA RECEITAS E SALDO ---
        
        # 4. TOTAL RECEITAS (Entradas)
        cursor.execute(f"SELECT SUM(valor_total) as total {sql_base_mes} AND tipo = 'receita'", params_mes)
        res_rec = cursor.fetchone()
        total_receitas = float(res_rec['total']) if res_rec and res_rec['total'] else 0.0

        # 5. SALDO ATUAL E LÓGICA DE STATUS
        saldo_atual = total_receitas - gasto_mes
        
        if saldo_atual < 0:
            status_financeiro = "Crítico (Estourado)"
            classe_alerta = "text-danger"
            sugestao = "Evite novos gastos! Suas despesas superam suas receitas."
        else:
            status_financeiro = "Dentro do Limite"
            classe_alerta = "text-success"
            sugestao = "Seu saldo está positivo. Mantenha o controle!"

        # --- FIM DOS NOVOS COMANDOS ---

        # 4. GRÁFICO POR CATEGORIA
        cursor.execute("""
            SELECT c.nome, SUM(t.valor_total) as total, c.cor
            FROM transacoes t
            JOIN categorias c ON t.categoria_id = c.id
            WHERE t.usuario_id = %s 
                AND MONTH(t.data_transacao) = %s 
                AND YEAR(t.data_transacao) = %s
                AND t.tipo = 'despesa'
            GROUP BY c.id
            HAVING total > 0
        """, params_mes)
        dados_grafico = cursor.fetchall()
        
        labels = [d['nome'] for d in dados_grafico]
        valores = [float(d['total']) for d in dados_grafico]
        cores = [d['cor'] for d in dados_grafico]

        # 5. MÉTODOS DE PAGAMENTO
        cursor.execute(f"SELECT metodo_pagamento, SUM(valor_total) as total {sql_base_mes} AND tipo = 'despesa' GROUP BY metodo_pagamento", params_mes)
        resumo_metodos = cursor.fetchall()
        labels_metodos = [row['metodo_pagamento'] for row in resumo_metodos]
        valores_metodos = [float(row['total']) for row in resumo_metodos]

        # 6. PRÓXIMAS CONTAS
        cursor.execute("SELECT id, descricao, valor_total, data_transacao FROM transacoes WHERE usuario_id = %s AND pago = 0 AND tipo = 'despesa' ORDER BY data_transacao ASC LIMIT 5", (user_id,))
        proximas_contas = cursor.fetchall()

        # 7. TOTAL ATRASADAS
        cursor.execute("SELECT COUNT(*) as total FROM transacoes WHERE usuario_id = %s AND pago = 0 AND data_transacao < %s AND tipo = 'despesa'", (user_id, hoje.date()))
        total_atrasadas = cursor.fetchone()['total']

        # 8. COMPARATIVO ANUAL (Entradas vs Saídas)
        cursor.execute("""
            SELECT 
                MONTH(data_transacao) as mes,
                SUM(CASE WHEN tipo = 'receita' THEN valor_total ELSE 0 END) as total_receita,
                SUM(CASE WHEN tipo = 'despesa' THEN valor_total ELSE 0 END) as total_despesa
            FROM transacoes 
            WHERE usuario_id = %s AND YEAR(data_transacao) = %s
            GROUP BY MONTH(data_transacao) 
            ORDER BY MONTH(data_transacao)
        """, (user_id, ano_atual))
        
        resumo_anual_fluxo = cursor.fetchall()
        
        # Inicializamos listas com 12 zeros para garantir que meses sem dados apareçam no gráfico
        receitas_anuais = [0.0] * 12
        despesas_anuais = [0.0] * 12

        for row in resumo_anual_fluxo:
            mes_idx = int(row['mes']) - 1
            receitas_anuais[mes_idx] = float(row['total_receita'])
            despesas_anuais[mes_idx] = float(row['total_despesa'])
        # 9. TOTAL INVESTIMENTOS (No mês focado)
        cursor.execute(f"SELECT SUM(valor_total) as total {sql_base_mes} AND tipo = 'investimento'", params_mes)
        res_inv = cursor.fetchone()
        total_investimentos = float(res_inv['total']) if res_inv and res_inv['total'] else 0.0

        # 10. COMPARATIVO ANUAL COM 3 BARRAS
        cursor.execute("""
            SELECT 
                MONTH(data_transacao) as mes,
                SUM(CASE WHEN tipo = 'receita' THEN valor_total ELSE 0 END) as total_receita,
                SUM(CASE WHEN tipo = 'despesa' THEN valor_total ELSE 0 END) as total_despesa,
                SUM(CASE WHEN tipo = 'investimento' THEN valor_total ELSE 0 END) as total_investimento
            FROM transacoes 
            WHERE usuario_id = %s AND YEAR(data_transacao) = %s
            GROUP BY MONTH(data_transacao) 
            ORDER BY MONTH(data_transacao)
        """, (user_id, ano_atual))

        resumo_anual_completo = cursor.fetchall()
        receitas_anuais = [0.0] * 12
        despesas_anuais = [0.0] * 12
        investimentos_anuais = [0.0] * 12

        for row in resumo_anual_completo:
            mes_idx = int(row['mes']) - 1
            receitas_anuais[mes_idx] = float(row['total_receita'])
            despesas_anuais[mes_idx] = float(row['total_despesa'])
            investimentos_anuais[mes_idx] = float(row['total_investimento'])
            
        # Cálculo da Taxa de Investimento (%)
        taxa_investimento = 0
        if total_receitas > 0:
            taxa_investimento = (total_investimentos / total_receitas) * 100
    
    
    finally:
        cursor.close()
        conn.close()
    
    return render_template('index.html', 
                           gasto_mes=gasto_mes,
                           total_pago=total_pago,
                           total_pendente=total_pendente,
                           total_receitas=total_receitas, # Enviando nova variável
                           total_despesas=gasto_mes,      # Enviando nova variável
                           saldo_atual=saldo_atual,       # Enviando nova variável
                           status_financeiro=status_financeiro,
                           classe_alerta=classe_alerta,
                           sugestao=sugestao,
                           labels=labels,
                           valores=valores,
                           cores=cores,
                           labels_metodos=labels_metodos,
                           valores_metodos=valores_metodos,
                           proximas_contas=proximas_contas,
                           total_atrasadas=total_atrasadas,
                           datetime_now=data_foco,
                           mes_atual_pt=mes_selecionado_pt,
                           data_anterior=data_anterior,
                           data_proxima=data_proxima,
                           receitas_anuais=receitas_anuais, 
                           despesas_anuais=despesas_anuais,
                           dados_anual=despesas_anuais,
                           total_investimentos=total_investimentos,
                           taxa_investimento=taxa_investimento,
                           investimentos_anuais=investimentos_anuais,
                           total_geral=total_geral)
    
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
    hoje = datetime.now().date()
    agora = datetime.now()
    
    # Filtros via URL (GET)
    busca = request.args.get('busca', '')
    mes_filtro = request.args.get('mes_filtro', '')
    ano_filtro = request.args.get('ano_filtro', '')
    metodo_filtro = request.args.get('metodo', '')
    status_filtro = request.args.get('status', '')
    filtro_atrasadas = request.args.get('filtro') == 'atrasadas'

    # Se não houver filtro, foca no mês atual
    if not any([busca, mes_filtro, ano_filtro, filtro_atrasadas, metodo_filtro, status_filtro]):
        mes_filtro = agora.strftime('%Y-%m')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True, buffered=True)

    try:
        # Busca anos para o seletor
        cursor.execute("SELECT DISTINCT YEAR(data_transacao) as ano FROM transacoes WHERE usuario_id = %s ORDER BY ano DESC", [user_id])
        anos_disponiveis = [row['ano'] for row in cursor.fetchall()]

        # Rótulo de exportação e Mês em Português para o Card de Diagnóstico
        mes_atual_pt = obter_nome_mes(agora.strftime('%m'))
        if mes_filtro:
            partes = mes_filtro.split('-')
            rotulo_exportar = f"{obter_nome_mes(partes[1])}/{partes[0]}"
        else:
            rotulo_exportar = "Geral"

        # Construção da Query (Incluso c.cor para o layout)
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
            elif ano_filtro:
                query_base += " AND YEAR(t.data_transacao) = %s"
                params.append(ano_filtro)

        if busca:
            query_base += " AND t.descricao LIKE %s"
            params.append(f"%{busca}%")
        if metodo_filtro:
            # ATENÇÃO: Verifique se no banco é 'metodo' ou 'metodo_pagamento'
            query_base += " AND t.metodo = %s" 
            params.append(metodo_filtro)
        if status_filtro:
            query_base += " AND t.pago = %s"
            params.append(status_filtro)

        # Execução principal trazendo a COR da categoria
        sql_lista = "SELECT t.*, c.nome as categoria_nome, c.cor as categoria_cor " + query_base + " ORDER BY t.data_transacao DESC"
        cursor.execute(sql_lista, tuple(params))
        transacoes = cursor.fetchall()

        # --- CÁLCULOS ---
        total_receita = sum(float(t['valor_total']) for t in transacoes if t['tipo'] == 'receita')
        # Despesas + Investimentos (ambos saem do saldo atual)
        total_despesa = sum(float(t['valor_total']) for t in transacoes if t['tipo'] in ['despesa', 'investimento'])
        
        saldo_final_mes = total_receita - total_despesa

        # Totais para os Cards inferiores (Baseados no filtro atual)
        cursor.execute("SELECT SUM(valor_total) as total " + query_base + " AND pago = 1", tuple(params))
        total_pago = float(cursor.fetchone()['total'] or 0)

        cursor.execute("SELECT SUM(valor_total) as total " + query_base + " AND pago = 0", tuple(params))
        total_pendente = float(cursor.fetchone()['total'] or 0)

        # Diagnóstico
        percentual_gasto = (total_despesa / total_receita * 100) if total_receita > 0 else 0
        
        if saldo_final_mes < 0:
            status_financeiro, sugestao = "Crítico", "Você está gastando mais do que recebe!"
        elif percentual_gasto > 80:
            status_financeiro, sugestao = "Atenção", "Cuidado, seus gastos estão próximos do seu limite."
        else:
            status_financeiro, sugestao = "Saudável", "Parabéns! Suas finanças estão equilibradas."

    finally:
        cursor.close()
        conn.close()

    return render_template('listagem.html', 
                           transacoes=transacoes,
                           total_receitas=total_receita,
                           total_despesas=total_despesa,
                           saldo_atual=saldo_final_mes,
                           titulo=titulo_pagina,
                           total_pago=total_pago,
                           total_pendente=total_pendente,
                           total_geral=total_receita, # Valor base para comparação
                           status_financeiro=status_financeiro,
                           sugestao=sugestao,
                           mes_atual_pt=mes_atual_pt,
                           rotulo_exportar=rotulo_exportar,
                           mes_ano_input=mes_filtro,
                           ano_selecionado=ano_filtro,
                           anos=anos_disponiveis)
    
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
        # Normalização consistente com a criação
        novo_nome = request.form.get('nome_categoria').strip().capitalize()
        nova_cor = request.form.get('cor')
        novo_tipo = request.form.get('tipo')
        
        try:
            cursor.execute("""
                UPDATE categorias 
                SET nome = %s, cor = %s, tipo = %s
                WHERE id = %s AND usuario_id = %s
            """, (novo_nome, nova_cor, novo_tipo, id, session['usuario_id']))
            conn.commit()
            flash('Categoria atualizada com sucesso!', 'success')
            return redirect(url_for('categorias'))
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash(f"Erro: Já existe uma categoria chamada '{novo_nome}'", "erro")
                return redirect(url_for('editar_categoria', id=id))
        finally:
            cursor.close()
            conn.close()

    # GET: Busca os dados para o formulário
    cursor.execute("SELECT * FROM categorias WHERE id = %s AND usuario_id = %s", (id, session['usuario_id']))
    categoria = cursor.fetchone()
    cursor.close()
    conn.close()

    if not categoria:
        flash('Categoria não encontrada!', 'erro')
        return redirect(url_for('categorias'))

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
    cursor = conn.cursor()

    try:
        # Tenta excluir a categoria
        cursor.execute("DELETE FROM categorias WHERE id = %s AND usuario_id = %s", (id, session['usuario_id']))
        conn.commit()
        flash('Categoria excluída com sucesso!', 'success')
    except mysql.connector.Error as err:
        # Se houver transações ligadas a essa categoria, o MySQL vai impedir a exclusão
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
        cursor.execute("SELECT id_transacao_pai, is_parcelado FROM transacoes WHERE id = %s AND usuario_id = %s", (id, user_id))
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
                    categoria_id = %s, metodo_pagamento = %s, tipo = %s, pago = %s, numero_parcelas = %s
                WHERE (id = %s OR id_transacao_pai = %s) AND usuario_id = %s
            """
            cursor.execute(sql, (nome_limpo, novo_total_p, nova_categoria, novo_metodo, tipo, pago, novo_total_p, id_pai, id_pai, user_id))
        else:
            # Atualização Individual
            sql = """
                UPDATE transacoes 
                SET descricao = %s, valor_total = %s, data_transacao = %s, 
                    categoria_id = %s, metodo_pagamento = %s, pago = %s, tipo = %s
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
        return redirect(url_for('login'))
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # 1. Busca o status atual E o tipo da transação
    cursor.execute("SELECT pago, tipo FROM transacoes WHERE id = %s", (id,))
    resultado = cursor.fetchone()
    
    if resultado:
        pago_atual = resultado[0]
        tipo = resultado[1]

        # 2. REGRA: Se for receita, novo_status será SEMPRE 1 (pago)
        if tipo == 'receita':
            novo_status = 1
        else:
            # Se for despesa, inverte o status normalmente
            novo_status = 0 if pago_atual == 1 else 1

        cursor.execute("UPDATE transacoes SET pago = %s WHERE id = %s", (novo_status, id))
        conn.commit()
        
        # Só mostra flash se for despesa (já que receita não muda)
        if tipo != 'receita':
            if novo_status == 1:
                flash("Conta marcada como paga!", "sucesso")
            else:
                flash("Conta marcada como pendente!", "sucesso")

    # 3. Recalcula os totais (Ajustado para considerar tipos corretamente)
    # Importante: O total pendente deve olhar apenas para DESPESAS
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN tipo = 'receita' THEN valor_total ELSE -valor_total END) as saldo,
            SUM(CASE WHEN pago = 1 THEN valor_total ELSE 0 END) as pago,
            SUM(CASE WHEN pago = 0 AND tipo = 'despesa' THEN valor_total ELSE 0 END) as pendente
        FROM transacoes 
        WHERE usuario_id = %s AND MONTH(data_transacao) = MONTH(CURRENT_DATE())
    """, (session['usuario_id'],))
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'status': 'sucesso',
            'novo_total': float(res[0] or 0),
            'novo_pago': float(res[1] or 0),
            'novo_pendente': float(res[2] or 0)
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