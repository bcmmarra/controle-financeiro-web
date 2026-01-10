from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import base64

# Gera a chave para o Web Push
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

private_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

print(f"PublicKey: {base64.urlsafe_b64encode(public_bytes).decode('utf-8').strip('=')}")
print(f"PrivateKey: {base64.urlsafe_b64encode(private_bytes).decode('utf-8').strip('=')}")