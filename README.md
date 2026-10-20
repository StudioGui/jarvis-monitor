# jarvis-monitor

Monitor 24h que roda no GitHub Actions a cada 5 minutos e avisa no Telegram quando um site cai,
lembra a cada hora enquanto estiver fora e avisa quando volta.

- Sites vigiados: lista `ALVOS` em `checar.py`.
- Token do bot e chat: segredos do repositório (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`), nunca no código.
- Teste manual: aba **Actions › Monitor 24h › Run workflow**, marcando "teste".
