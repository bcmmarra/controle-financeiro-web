import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

def testar_envio():
    print(f"Tentando enviar e-mail de: {EMAIL_USER}...")
    
    msg = EmailMessage()
    msg['Subject'] = "Teste de Conexão - Descomplica MyFinance"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER  # Envia para você mesmo
    msg.set_content("Se você recebeu isso, a integração com o Gmail está funcionando perfeitamente!")

    try:
        # Porta 465 é a recomendada para SSL no PythonAnywhere
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print("✅ Sucesso! O e-mail foi enviado.")
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("\nDica: Verifique se você gerou uma 'Senha de App' no Google.")

if __name__ == "__main__":
    testar_envio()