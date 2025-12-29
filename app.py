from flask import Flask, render_template, request, redirect
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
        return "Lançamento realizado com sucesso! <a href='/'>Voltar</a>"
    except Exception as e:
        return f"Erro ao salvar: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)