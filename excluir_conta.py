import mysql.connector
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
from app import db_config  # Importa a config do banco do seu app principal
from dotenv import load_dotenv
import os

# Carrega as variáveis do arquivo .env
load_dotenv()

# Pegando as credenciais do .env
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

def enviar_aviso_final(destinatario, nome):
    msg = EmailMessage()
    msg['Subject'] = "Atenção: Sua conta será excluída em 3 dias! ⚠️"
    msg['From'] = f"Descomplica MyFinance <{EMAIL_USER}>"
    msg['To'] = destinatario
    
    conteudo = f"""
    Olá, {nome}.
    
    Notamos que sua conta no Descomplica MyFinance está inativa para exclusão.
    Conforme solicitado, todos os seus dados (transações, categorias e perfil) serão 
    eliminados permanentemente daqui a 3 dias.
    
    Se mudou de ideia e quer manter seu histórico financeiro, basta fazer 
    login na sua conta antes do prazo terminar.
    
    Caso contrário, não precisa fazer nada.
    
    Até breve,
    Equipe Descomplica MyFinance
    (031) 99185-3333 (zap)
    """
    msg.set_content(conteudo)
    
    try:
        # Usando a porta 465 para SSL (Gmail)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print(f"✅ Aviso enviado com sucesso para: {destinatario}")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail para {destinatario}: {e}")

def realizar_manutencao():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    hoje = datetime.now()
    
    try:
        # --- PARTE 1: AVISAR QUEM ESTÁ A 3 DIAS DO FIM ---
        # Buscamos quem vence em 3 dias E que ainda não foi avisado
        data_aviso = (hoje + timedelta(days=3)).date()
        
        cursor.execute("""
            SELECT id, nome, email, aviso_exclusao_enviado 
            FROM usuarios 
            WHERE status_ativo = 0 
            AND DATE(data_exclusao_programada) = %s
            AND (aviso_exclusao_enviado = 0 OR aviso_exclusao_enviado IS NULL)
        """, (data_aviso,))
        
        prestes_a_sair = cursor.fetchall()
        for user in prestes_a_sair:
            enviar_aviso_final(user['email'], user['nome'])
            # Marca como avisado para não repetir o e-mail amanhã
            cursor.execute("UPDATE usuarios SET aviso_exclusao_enviado = 1 WHERE id = %s", (user['id'],))
        
        conn.commit()

        # --- PARTE 2: EXCLUSÃO DEFINITIVA ---
        cursor.execute("""
            SELECT id FROM usuarios 
            WHERE status_ativo = 0 
            AND data_exclusao_programada <= %s
        """, (hoje,))
        
        expirados = cursor.fetchall()

        for user in expirados:
            u_id = user['id']
            # Deletando em ordem para respeitar Constraints
            cursor.execute("DELETE FROM inteligencia_regras WHERE usuario_id = %s", (u_id,))
            cursor.execute("DELETE FROM transacoes WHERE usuario_id = %s", (u_id,))
            cursor.execute("DELETE FROM categorias WHERE usuario_id = %s", (u_id,))
            cursor.execute("DELETE FROM inscricoes_push WHERE usuario_id = %s", (u_id,))
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (u_id,))
            print(f"🗑️ Dados do usuário {u_id} apagados permanentemente.")
            
        conn.commit()
        
    except Exception as e:
        print(f"⚠️ Falha na manutenção: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    realizar_manutencao()