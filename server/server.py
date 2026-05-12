import sys
import time
import threading
import queue
from concurrent import futures
from datetime import datetime

import grpc
sys.path.insert(0, ".")
from proto import chat_pb2, chat_pb2_grpc
from server import database as db

# ─── ESTADO EM MEMÓRIA ────────────────────────────────────────────────────────
# Guarda as filas de stream de cada usuário online
# { phone: [queue, queue, ...] }  (pode ter múltiplas conexões)

_subscribers: dict[str, list] = {} # usuario/lista de fila de mensagens
_lock = threading.Lock()

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _status_to_proto(status_int: int):
    mapping = {
        0: chat_pb2.SENT,
        1: chat_pb2.DELIVERED,
        2: chat_pb2.READ,
    }
    return mapping.get(status_int, chat_pb2.SENT)

def _dict_to_proto_message(m: dict) -> chat_pb2.Message:
    return chat_pb2.Message(
        id        = m["id"],
        sender    = m["sender"],
        receiver  = m["receiver"],
        content   = m["content"],
        timestamp = m["timestamp"],
        status    = _status_to_proto(m["status"]),
    )

def _is_online(phone: str) -> bool:
    with _lock:
        return bool(_subscribers.get(phone))

def _push_to_subscriber(phone: str, proto_msg: chat_pb2.Message):
    """Envia mensagem para todas as filas ativas do usuário."""
    with _lock:
        queues = _subscribers.get(phone, [])
        for q in queues:
            q.put(proto_msg)

class ChatServicer(chat_pb2_grpc.ChatServiceServicer):

    def Register(self, request, context):
        success = db.create_user(request.phone, request.name, request.nickname)
        if success:
            print(f"[SERVER] Novo usuário: {request.name} ({request.phone})")
            return chat_pb2.RegisterResponse(
                success=True,
                message=f"Usuário '{request.nickname}' cadastrado com sucesso!"
            )
        return chat_pb2.RegisterResponse(
            success=False,
            message="Telefone já cadastrado."
        )

    def Login(self, request, context):
        if db.user_exists(request.phone):
            user = db.get_user(request.phone)
            print(f"[SERVER] Usuário logado: {user['nickname']} ({request.phone})")
            return chat_pb2.LoginResponse(
                success=True,
                nickname=user['nickname'],
                message="Login bem-sucedido."
            )
        return chat_pb2.LoginResponse(
            success=False,
            nickname="",
            message="Usuário não encontrado."
        )

    def SendMessage(self, request, context):
        # Valida remetente e destinatário
        if not db.user_exists(request.sender):
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Remetente não encontrado.")
            return chat_pb2.SendMessageResponse(success=False)

        if not db.user_exists(request.receiver):
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Destinatário não encontrado.")
            return chat_pb2.SendMessageResponse(success=False)

        # Persiste com status SENT
        msg = db.save_message(request.sender, request.receiver, request.content)

        # Se destinatário está online -- marca DELIVERED e envia via stream
        if _is_online(request.receiver):
            db.mark_delivered(request.receiver)
            msg["status"] = db.STATUS_DELIVERED
            proto_msg = _dict_to_proto_message(msg)
            _push_to_subscriber(request.receiver, proto_msg)
            print(f"[SERVER] Mensagem entregue em tempo real para {request.receiver}")
        else:
            proto_msg = _dict_to_proto_message(msg)
            print(f"[SERVER] {request.receiver} offline — mensagem guardada como SENT")

        return chat_pb2.SendMessageResponse(
            success    = True,
            message_id = msg["id"],
            status     = _status_to_proto(msg["status"]),
        )

    def GetHistory(self, request, context):
        messages = db.get_history(request.user_a, request.user_b)
        proto_msgs = [_dict_to_proto_message(m) for m in messages]
        return chat_pb2.GetHistoryResponse(messages=proto_msgs)

    def MarkAsRead(self, request, context):
        db.mark_read(request.reader, request.conversation_with)

        # notifica o remetente original (se online) que foi lido
        # busca histórico para pegar as msgs atualizadas e enviar ao remetente
        history = db.get_history(request.reader, request.conversation_with)
        for m in history:
            if m["sender"] == request.conversation_with and m["status"] == db.STATUS_READ:
                proto_msg = _dict_to_proto_message(m)
                _push_to_subscriber(request.conversation_with, proto_msg)

        return chat_pb2.MarkAsReadResponse(success=True)

    def Subscribe(self, request, context):
        phone = request.phone

        if not db.user_exists(phone):
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Usuário não encontrado.")
            return

        print(f"[SERVER] {phone} conectou ao stream")

        # Fila de mensagens desse cliente (usando thread-safe Queue para evitar polling)
        client_queue = queue.Queue()
        with _lock:
            _subscribers.setdefault(phone, []).append(client_queue)

        # Ao conectar, marca pendentes como DELIVERED
        db.mark_delivered(phone)

        # Registra callback para quando o cliente desconectar
        def on_disconnect():
            client_queue.put(None)
        context.add_callback(on_disconnect)

        try:
            while True:
                # Aguarda mensagem bloqueando a thread, sem fazer polling de status
                msg = client_queue.get()
                if msg is None:
                    break
                yield msg
        finally:
            # Limpeza ao desconectar
            with _lock:
                if phone in _subscribers:
                    try:
                        _subscribers[phone].remove(client_queue)
                    except ValueError:
                        pass
                    if not _subscribers[phone]:
                        del _subscribers[phone]
            print(f"[SERVER] {phone} desconectou do stream")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def serve():
    db.init_db()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatServicer(), server)

    address = "[::]:50051"
    server.add_insecure_port(address)
    server.start()
    print(f"[SERVER] Servidor gRPC rodando em {address}")
    print("[SERVER] Ctrl+C para encerrar\n")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n[SERVER] Encerrando...")
        server.stop(0)

if __name__ == "__main__":
    serve()