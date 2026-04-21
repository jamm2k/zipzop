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

    # 1. Servidor (usando -X utf8 para que a nova janela também suporte emojis)
    abrir_janela(
        "ZipZop — Servidor",
        f"{PYTHON} -X utf8 server/server.py"
    )
    print("  ✅ Servidor iniciado")

    # Aguarda o servidor subir antes dos clientes
    time.sleep(2)

    # 2. Cliente A
    abrir_janela(
        "ZipZop — Cliente A",
        f"{PYTHON} -X utf8 client/client.py"
    )
    print(" Cliente A iniciado")

    time.sleep(0.5)

    # 3. Cliente B
    abrir_janela(
        "ZipZop — Cliente B",
        f"{PYTHON} -X utf8 client/client.py"
    )
    print(" Cliente B iniciado")

    print("\n  Três janelas abertas! Bom teste 💬")

if __name__ == "__main__":
    main()