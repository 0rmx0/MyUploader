from cryptography.fernet import Fernet
import json
import base64
import getpass


def create_encrypted_config():
    # Saisie manuelle de la clé de chiffrement
    print("=== S3 Configuration Encryption ===")
    encryption_password = getpass.getpass("Enter a secure encryption password: ").encode()
    confirm_password = getpass.getpass("Confirm your encryption password: ").encode()

    if encryption_password != confirm_password:
        print("Passwords do not match. Exiting.")
        return

    # Création de la clé à partir du mot de passe saisi
    encryption_key = base64.urlsafe_b64encode(encryption_password.ljust(32)[:32])  # Complète à 32 octets si nécessaire
    fernet = Fernet(encryption_key)

    # Saisie des paramètres S3
    bucket_name = input("Enter your S3 bucket name: ")
    endpoint_url = input("Enter your S3 region: ")
    access_key = input("Enter your S3 access key: ")
    secret_key = input("Enter your S3 secret key: ")

    # Chiffrement des clés d'accès
    access_key_encrypted = fernet.encrypt(access_key.encode()).decode()
    secret_key_encrypted = fernet.encrypt(secret_key.encode()).decode()

    # Création du fichier de configuration
    config = {
        "bucket_name": bucket_name,
        "endpoint_url": endpoint_url,
        "access_key_encrypted": access_key_encrypted,
        "secret_key_encrypted": secret_key_encrypted
    }

    config_file = "config.json"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=4)

    print(f"Configuration file '{config_file}' created successfully!")
    print("Keep your encryption password secure; it will be required during upload.")


if __name__ == "__main__":
    create_encrypted_config()