import subprocess
import time
import sys
import os

# Força o uso do UTF-8 na saída do console para suportar os emojis nas mensagens
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

def abrir_janela(titulo, comando):
    """Abre um novo terminal Windows com o comando dado."""
    subprocess.Popen(
        f'start "{titulo}" cmd /k "{comando}"',
        shell=True,
        cwd=ROOT
    )

def main():
    print("Iniciando ZipZop...")

    # 1. Servidor na VM do Vagrant
    abrir_janela(
        "ZipZop — Servidor (Vagrant)",
        'vagrant ssh server -c "cd /vagrant ; python3 server/server.py"'
    )
    print("  ✅ Conectando ao Servidor...")

    # Aguarda um pouco para os próximos terminais
    time.sleep(2)

    # 2. Cliente 1 na VM do Vagrant
    abrir_janela(
        "ZipZop — Cliente 1 (Vagrant)",
        'vagrant ssh client1 -c "cd /vagrant ; export ZIPZOP_SERVER=192.168.56.10:50051 ; python3 client/client.py"'
    )
    print("  ✅ Conectando ao Cliente 1...")

    time.sleep(0.5)

    # 3. Cliente 2 na VM do Vagrant
    abrir_janela(
        "ZipZop — Cliente 2 (Vagrant)",
        'vagrant ssh client2 -c "cd /vagrant ; export ZIPZOP_SERVER=192.168.56.10:50051 ; python3 client/client.py"'
    )
    print("  ✅ Conectando ao Cliente 2...")

if __name__ == "__main__":
    main()