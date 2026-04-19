import sys
import threading
import grpc

sys.path.insert(0, ".")
from proto import chat_pb2, chat_pb2_grpc

SERVER_ADDRESS = "localhost:50051"

# CONEXÃO ──────────────────────────────────────────────────────────────────

def get_stub():
    channel = grpc.insecure_channel(SERVER_ADDRESS)
    return chat_pb2_grpc.ChatServiceStub(channel), channel

# STATUS VISUAL ────────────────────────────────────────────────────────────

STATUS_ICON = {
    chat_pb2.SENT:      "✓",
    chat_pb2.DELIVERED: "✓✓",
    chat_pb2.READ:      "✓✓🔵",
}

# STREAM LISTENER ──────────────────────────────────────────────────────────

def listen_for_messages(stub, my_phone, stop_event):
    """Roda em thread separada — escuta mensagens em tempo real."""
    try:
        req = chat_pb2.SubscribeRequest(phone=my_phone)
        for msg in stub.Subscribe(req):
            if stop_event.is_set():
                break
            # Mensagem recebida de alguém
            if msg.sender != my_phone:
                print(f"\n  📩 [{msg.timestamp[:19]}] {msg.sender}: {msg.content}")
            # Atualização de status de mensagem propria (ex: lida pelo outro)
            else:
                icon = STATUS_ICON.get(msg.status, "?")
                print(f"\n  [{icon}] Sua mensagem foi atualizada: '{msg.content[:30]}'")
            print("  > ", end="", flush=True)
    except grpc.RpcError:
        if not stop_event.is_set():
            print("\n[CLIENTE] Conexão com o servidor perdida.")

# AÇÕES ────────────────────────────────────────────────────────────────────

def action_register(stub):
    print("\n── Cadastro ──")
    phone    = input("  Telefone (ex: 21999990001): ").strip()
    name     = input("  Nome completo: ").strip()
    nickname = input("  Apelido: ").strip()

    resp = stub.Register(chat_pb2.RegisterRequest(
        phone=phone, name=name, nickname=nickname
    ))
    print(f"  {'✅' if resp.success else '❌'} {resp.message}")
    return phone if resp.success else None

def action_send(stub, my_phone):
    print("\n── Enviar mensagem ──")
    receiver = input("  Telefone do destinatário: ").strip()
    content  = input("  Mensagem: ").strip()

    resp = stub.SendMessage(chat_pb2.SendMessageRequest(
        sender=my_phone, receiver=receiver, content=content
    ))
    if resp.success:
        icon = STATUS_ICON.get(resp.status, "?")
        print(f"  ✅ Enviada {icon}  (id: {resp.message_id[:8]}...)")
    else:
        print("  ❌ Falha ao enviar.")

def action_history(stub, my_phone):
    print("\n── Histórico ──")
    other = input("  Telefone do outro usuário: ").strip()

    #marca como lido ao abrir o historico
    stub.MarkAsRead(chat_pb2.MarkAsReadRequest(
        reader=my_phone, conversation_with=other
    ))

    resp = stub.GetHistory(chat_pb2.GetHistoryRequest(
        user_a=my_phone, user_b=other
    ))

    if not resp.messages:
        print("  (nenhuma mensagem ainda)")
        return

    print(f"\n  ── Conversa com {other} ──")
    for m in resp.messages:
        icon      = STATUS_ICON.get(m.status, "?")
        direction = "→" if m.sender == my_phone else "←"
        time_str  = m.timestamp[:19].replace("T", " ")
        print(f"  {direction} [{time_str}] {m.content}  {icon}")

# MENU PRINCIPAL ───────────────────────────────────────────────────────────

def menu_logged_out(stub):
    """Menu antes de fazer login."""
    while True:
        print("\n══════════════════════")
        print("      ZipZop 💬")
        print("══════════════════════")
        print("  1. Cadastrar")
        print("  2. Entrar")
        print("  0. Sair")
        choice = input("  > ").strip()

        if choice == "1":
            phone = action_register(stub)
            if phone:
                return phone
        elif choice == "2":
            phone = input("\n  Seu telefone: ").strip()
            from server import database as db
            if db.user_exists(phone):
                user = db.get_user(phone)
                print(f"  ✅ Bem-vindo, {user['nickname']}!")
                return phone
            else:
                print("  ❌ Usuário não encontrado.")
        elif choice == "0":
            sys.exit(0)

def menu_logged_in(stub, my_phone, stop_event):
    """Menu principal após login."""
    while True:
        print("\n──────────────────────")
        print(f"  Logado: {my_phone}")
        print("  1. Enviar mensagem")
        print("  2. Ver histórico")
        print("  0. Sair")
        choice = input("  > ").strip()

        if choice == "1":
            action_send(stub, my_phone)
        elif choice == "2":
            action_history(stub, my_phone)
        elif choice == "0":
            stop_event.set()
            print("  Até logo! 👋")
            sys.exit(0)

# MAIN ─────────────────────────────────────────────────────────────────────

def main():
    stub, channel = get_stub()

    try:
        # Login / cadastro
        my_phone = menu_logged_out(stub)

        # Inicia listener de mensagens em background
        stop_event = threading.Event()
        listener   = threading.Thread(
            target=listen_for_messages,
            args=(stub, my_phone, stop_event),
            daemon=True
        )
        listener.start()

        # Menu principal
        menu_logged_in(stub, my_phone, stop_event)

    except KeyboardInterrupt:
        print("\n[CLIENTE] Encerrando...")
    finally:
        channel.close()

if __name__ == "__main__":
    main()