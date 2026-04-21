import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "zipzop.db"

# ─── CONEXÃO ──────────────────────────────────────────────────────────────────

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # retorna dicionarios em vez de tuplas
    conn.execute("PRAGMA journal_mode=WAL")  #suporte a leituras concorrentes
    return conn

# ─── INICIALIZAÇÃO DAS TABELAS ────────────────────────────────────────────────

def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                phone    TEXT PRIMARY KEY,
                name     TEXT NOT NULL,
                nickname TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         TEXT PRIMARY KEY,
                sender     TEXT NOT NULL,
                receiver   TEXT NOT NULL,
                content    TEXT NOT NULL,
                timestamp  TEXT NOT NULL,
                status     INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (sender)   REFERENCES users(phone),
                FOREIGN KEY (receiver) REFERENCES users(phone)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages (sender, receiver);
        """)
    print(f"[DB] Banco inicializado em: {DB_PATH}")

# ─── USUÁRIOS ─────────────────────────────────────────────────────────────────

def create_user(phone: str, name: str, nickname: str) -> bool:
    """Cadastra novo usuário. Retorna False se o telefone já existir."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (phone, name, nickname, created_at) VALUES (?, ?, ?, ?)",
                (phone, name, nickname, datetime.utcnow().isoformat())
            )
        return True
    except sqlite3.IntegrityError:
        return False  # telefone já cadastrado (PRIMARY KEY duplicada)

def get_user(phone: str) -> dict | None:
    """Busca usuário pelo telefone. Retorna None se não existir."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE phone = ?", (phone,)
        ).fetchone()
    return dict(row) if row else None

def user_exists(phone: str) -> bool:
    return get_user(phone) is not None

# ─── MENSAGENS ────────────────────────────────────────────────────────────────

# Status espelha o enum do .proto:
STATUS_SENT      = 0
STATUS_DELIVERED = 1
STATUS_READ      = 2

def save_message(sender: str, receiver: str, content: str) -> dict:
    """
    Persiste uma nova mensagem.
    Status inicial = SENT (0).
    Retorna o dicionario da mensagem criada
    """
    msg_id    = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    status    = STATUS_SENT

    with get_connection() as conn:
        conn.execute(
            """INSERT INTO messages (id, sender, receiver, content, timestamp, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (msg_id, sender, receiver, content, timestamp, status)
        )

    return {
        "id":        msg_id,
        "sender":    sender,
        "receiver":  receiver,
        "content":   content,
        "timestamp": timestamp,
        "status":    status,
    }

def get_history(user_a: str, user_b: str) -> list[dict]:
    """
    Retorna todas as mensagens trocadas entre user_a e user_b,
    ordenadas por timestamp.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM messages
               WHERE (sender = ? AND receiver = ?)
                  OR (sender = ? AND receiver = ?)
               ORDER BY timestamp ASC""",
            (user_a, user_b, user_b, user_a)
        ).fetchall()
    return [dict(r) for r in rows]

def mark_delivered(receiver: str):
    """
    Marca como DELIVERED todas as mensagens destinadas a 'receiver'
    que ainda estão como SENT.
    Chamado quando o usuario se conecta.
    """
    with get_connection() as conn:
        conn.execute(
            """UPDATE messages
               SET status = ?
               WHERE receiver = ? AND status = ?""",
            (STATUS_DELIVERED, receiver, STATUS_SENT)
        )

def mark_read(reader: str, conversation_with: str):
    """
    Marca como READ todas as mensagens enviadas por 'conversation_with'
    para 'reader' que ainda não foram lidas.
    Chamado quando o usuário abre uma conversa.
    """
    with get_connection() as conn:
        conn.execute(
            """UPDATE messages
               SET status = ?
               WHERE sender = ? AND receiver = ? AND status < ?""",
            (STATUS_READ, conversation_with, reader, STATUS_READ)
        )

def get_message(msg_id: str) -> dict | None:
    """Busca uma mensagem específica pelo ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (msg_id,)
        ).fetchone()
    return dict(row) if row else None