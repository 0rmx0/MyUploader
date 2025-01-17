import os
import json
import boto3
import base64
from cryptography.fernet import Fernet
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import sys
import platform


def charger_configuration(chemin_config="config.json"):
    """Charger et retourner la configuration."""
    try:
        with open(chemin_config, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement du fichier de configuration : {e}")
        exit(1)


def decrypter_cles(config, mot_de_passe):
    """Décrypter les clés d'accès et secrètes."""
    try:
        cle_chiffrement = base64.urlsafe_b64encode(mot_de_passe.encode().ljust(32)[:32])  # Clé dérivée
        fernet = Fernet(cle_chiffrement)
        cle_acces = fernet.decrypt(config["access_key_encrypted"].encode()).decode()
        cle_secrete = fernet.decrypt(config["secret_key_encrypted"].encode()).decode()
        return cle_acces, cle_secrete
    except Exception as e:
        print(f"Erreur lors du décryptage des clés : {e}")
        exit(1)


def telecharger_fichier_en_plusieurs_parties(client_s3, nom_bucket, chemin_fichier, cle_s3, taille_partie=10 * 1024 * 1024):
    """Télécharger un fichier volumineux avec un téléversement multipartite."""
    try:
        multipart_upload = client_s3.create_multipart_upload(Bucket=nom_bucket, Key=cle_s3)
        upload_id = multipart_upload["UploadId"]
    except Exception as e:
        print(f"Erreur lors de l'initialisation du téléversement multipartite : {e}")
        return

    parties = []
    with open(chemin_fichier, "rb") as f:
        numero_partie = 1
        while True:
            donnees = f.read(taille_partie)
            if not donnees:
                break
            try:
                print(f"Téléversement de la partie {numero_partie}...")
                response = client_s3.upload_part(
                    Bucket=nom_bucket,
                    Key=cle_s3,
                    PartNumber=numero_partie,
                    UploadId=upload_id,
                    Body=donnees,
                )
                parties.append({"PartNumber": numero_partie, "ETag": response["ETag"]})
            except Exception as e:
                print(f"Erreur lors du téléversement de la partie {numero_partie} : {e}")
                return

            numero_partie += 1

    try:
        client_s3.complete_multipart_upload(
            Bucket=nom_bucket,
            Key=cle_s3,
            UploadId=upload_id,
            MultipartUpload={"Parts": parties},
        )
        print("Téléversement terminé avec succès.")
    except Exception as e:
        print(f"Erreur lors de la finalisation du téléversement : {e}")
        client_s3.abort_multipart_upload(Bucket=nom_bucket, Key=cle_s3, UploadId=upload_id)


def televerser_fichier_ou_repertoire(config, chemin, mot_de_passe):
    """Téléverser un fichier unique ou un répertoire vers S3."""
    cle_acces, cle_secrete = decrypter_cles(config, mot_de_passe)
    client_s3 = boto3.client(
        "s3", aws_access_key_id=cle_acces, aws_secret_access_key=cle_secrete, region_name=config["region"]
    )
    nom_bucket = config["bucket_name"]

    if os.path.isfile(chemin):
        cle_s3 = os.path.basename(chemin)
        telecharger_fichier_en_plusieurs_parties(client_s3, nom_bucket, chemin, cle_s3)
    elif os.path.isdir(chemin):
        for racine, _, fichiers in os.walk(chemin):
            for fichier in fichiers:
                chemin_fichier = os.path.join(racine, fichier)
                cle_s3 = os.path.relpath(chemin_fichier, chemin).replace("\\", "/")
                telecharger_fichier_en_plusieurs_parties(client_s3, nom_bucket, chemin_fichier, cle_s3)
    else:
        print(f"Chemin invalide : {chemin}")


def lancer_config_generator():
    """Lancer le script config_generator.py dans une nouvelle fenêtre de terminal."""
    try:
        if platform.system() == "Linux":
            subprocess.run(["gnome-terminal", "--", sys.executable, "config_generator.py"], check=True)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["osascript", "-e", f'tell app "Terminal" to do script "{sys.executable} config_generator.py"'], check=True)
        elif platform.system() == "Windows":
            subprocess.run(["start", "cmd", "/k", sys.executable, "config_generator.py"], shell=True, check=True)
        else:
            raise NotImplementedError("Unsupported OS")
        messagebox.showinfo("Succès", "Le script de génération de configuration a été exécuté avec succès.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erreur", f"Échec de l'exécution du script : {e}")
    except NotImplementedError as e:
        messagebox.showerror("Erreur", str(e))


def selectionner_repertoire_ou_fichier(config):
    """Créer une interface graphique pour sélectionner un répertoire ou un fichier."""
    def parcourir_repertoire():
        chemin = filedialog.askdirectory()
        if chemin:
            champ_chemin.delete(0, tk.END)
            champ_chemin.insert(0, chemin)

    def parcourir_fichier():
        chemin = filedialog.askopenfilename()
        if chemin:
            champ_chemin.delete(0, tk.END)
            champ_chemin.insert(0, chemin)

    def lancer_televersement():
        chemin = champ_chemin.get()
        mot_de_passe = champ_mot_de_passe.get()

        if not chemin or not mot_de_passe:
            messagebox.showerror("Erreur", "Le chemin et le mot de passe sont obligatoires !")
            return

        if not os.path.exists(chemin):
            messagebox.showerror("Erreur", "Le chemin sélectionné n'existe pas !")
            return

        try:
            televerser_fichier_ou_repertoire(config, chemin, mot_de_passe)
            messagebox.showinfo("Succès", "Téléversement terminé avec succès !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec du téléversement : {e}")

    # Interface graphique Tkinter
    root = tk.Tk()
    root.title("Téléverseur S3")

    tk.Label(root, text="Sélectionner un fichier/répertoire :").grid(row=0, column=0, padx=10, pady=5, sticky="w")
    champ_chemin = tk.Entry(root, width=50)
    champ_chemin.grid(row=0, column=1, padx=10, pady=5, sticky="w")
    tk.Button(root, text="Parcourir fichier", command=parcourir_fichier).grid(row=0, column=2, padx=5, pady=5)
    tk.Button(root, text="Parcourir répertoire", command=parcourir_repertoire).grid(row=0, column=3, padx=5, pady=5)

    tk.Label(root, text="Mot de passe de chiffrement :").grid(row=1, column=0, padx=10, pady=5, sticky="w")
    champ_mot_de_passe = tk.Entry(root, show="*", width=50)
    champ_mot_de_passe.grid(row=1, column=1, columnspan=3, padx=10, pady=5, sticky="w")

    tk.Button(root, text="Lancer le téléversement", command=lancer_televersement).grid(row=2, column=0, columnspan=4, pady=10)
    tk.Button(root, text="Générer config", command=lancer_config_generator).grid(row=3, column=0, columnspan=4, pady=10)

    # Ajouter le numéro de version en bas à droite
    version_label = tk.Label(root, text="Version 0.0.2", font=("Arial", 8))
    version_label.place(relx=1.0, rely=1.0, anchor='se', x=-10, y=-10)

    root.mainloop()


if __name__ == "__main__":
    config = charger_configuration()
    selectionner_repertoire_ou_fichier(config)
