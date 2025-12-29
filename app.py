from flask import Flask
import mysql.connector

app = Flask(__name__)

# CONFIGURAÇÃO DO SEU BANCO (Ajuste a senha!)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Dc524876_*',
    'database': 'controle_financeiro'
}

@app.route('/')
def testar_conexao():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()
        conn.close()
        return f"Conectado com sucesso ao banco: {db_name[0]}"
    except Exception as e:
        return f"Erro ao conectar: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)