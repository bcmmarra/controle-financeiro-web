from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from datetime import datetime, timedelta

app = Flask(__name__)

# CONFIGURAÇÃO DO SEU BANCO (Ajuste a senha!)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Dc524876_*',
    'database': 'controle_financeiro'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/salvar', methods=['POST'])
def salvar():
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
            
            # Por enquanto usando usuario_id=1 e categoria_id=1 para teste
            valores = (1, 1, valor_parcela, f"{descricao} ({i+1}/{num_parcelas})", data_parcela, metodo, 'despesa', num_parcelas > 1, num_parcelas, i+1)
            
            cursor.execute(sql, valores)
        
        conn.commit()
        conn.close()
        return redirect(url_for('listagem'))
    except Exception as e:
        return f"Erro ao salvar: {str(e)}"


@app.route('/listagem')
def listagem():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # Busca transações
        cursor.execute("SELECT t.*, c.nome as categoria_nome FROM transacoes t JOIN categorias c ON t.categoria_id = c.id ORDER BY t.data_transacao DESC")
        dados = cursor.fetchall()
        
        # SQL para somar o total gasto
        cursor.execute("SELECT SUM(valor_total) as total FROM transacoes")
        soma = cursor.fetchone()
        total_gasto = soma['total'] if soma['total'] else 0.0
        
        cursor.close()
        conn.close()
        return render_template('listagem.html', transacoes=dados, total_gasto=total_gasto)
    except Exception as e:
        return f"Erro: {str(e)}"

@app.route('/excluir/<int:id>')
def excluir(id):
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

if __name__ == '__main__':
    app.run(debug=True)