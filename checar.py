"""Monitor 24h do Jarvis (roda no GitHub Actions a cada 5 minutos).

Avisa no Telegram quando um site cai, lembra a cada hora enquanto estiver fora
e avisa quando volta. O estado fica em estado.json (gravado pelo workflow).
Só usa a biblioteca padrão do Python.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ALVOS = [
    {"nome": "VeciYa", "url": "https://veciya.cl/planes", "texto": "Planes"},
]
LEMBRETE = timedelta(minutes=60)
MANTER_VIVO = timedelta(days=7)  # grava o arquivo ao menos 1x/semana para o GitHub não pausar o agendamento
ESTADO = Path(__file__).with_name("estado.json")
FUSO = ZoneInfo("America/Santiago")


def testar(alvo: dict) -> str | None:
    """None se está OK; senão, o motivo."""
    req = urllib.request.Request(alvo["url"], headers={"User-Agent": "JarvisMonitor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            corpo = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return "HTTP 503 (fora do ar ou em manutenção)" if e.code == 503 else f"HTTP {e.code}"
    except Exception as e:
        return f"não respondeu ({type(e).__name__})"
    if alvo["texto"] not in corpo:
        return f"página abriu sem o texto \"{alvo['texto']}\""
    return None


def telegram(texto: str) -> None:
    token, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Telegram não configurado")
        return
    dados = json.dumps({"chat_id": chat, "text": texto, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=dados,
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30).read()


def minutos(desde: str, agora: datetime) -> int:
    return int((agora - datetime.fromisoformat(desde)).total_seconds() // 60)


def main() -> None:
    agora = datetime.now(FUSO)
    if "--teste" in sys.argv:
        telegram("✅ <b>Monitor 24h ativo</b> (GitHub). Vigiando: " + ", ".join(a["nome"] for a in ALVOS))
        return

    estado = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
    original = json.dumps(estado, sort_keys=True)

    for alvo in ALVOS:
        nome = alvo["nome"]
        motivo = testar(alvo)
        if motivo:  # confirma antes de alarmar: falhas de segundos são comuns
            time.sleep(30)
            motivo = testar(alvo)
        atual = estado.setdefault(nome, {"status": "ok"})  # registra o site desde a 1ª rodada (o painel lê daqui)
        print(f"{nome}: {'OK' if not motivo else 'FORA'}")

        if motivo and atual["status"] == "ok":
            telegram(f"🔴 <b>{nome} fora do ar</b>\n{motivo}\n{alvo['url']}")
            estado[nome] = {"status": "fora", "desde": agora.isoformat(), "ultimo_alerta": agora.isoformat()}
        elif motivo and agora - datetime.fromisoformat(atual["ultimo_alerta"]) >= LEMBRETE:
            telegram(f"🔴 <b>{nome} continua fora</b> há {minutos(atual['desde'], agora)} min\n{motivo}")
            atual["ultimo_alerta"] = agora.isoformat()
        elif not motivo and atual["status"] == "fora":
            telegram(f"🟢 <b>{nome} voltou</b> depois de {minutos(atual['desde'], agora)} min fora")
            estado[nome] = {"status": "ok"}

    gravado = estado.get("_gravado")
    if json.dumps(estado, sort_keys=True) != original or not gravado or \
            agora - datetime.fromisoformat(gravado) >= MANTER_VIVO:
        estado["_gravado"] = agora.isoformat()
        ESTADO.write_text(json.dumps(estado, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
