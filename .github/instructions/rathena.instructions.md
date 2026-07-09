---
applyTo: "**/{conf,db,npc,src,sql-files}/**/*"
---

# Instruções específicas para rAthena

- Priorize customizações em diretórios de importação/customização.
- Não edite arquivos upstream sem justificar.
- Preserve compatibilidade com updates futuros do emulador.
- Ao alterar rates, level máximo, jobs, drops ou skills, documente impacto de balanceamento.
- Sempre indicar como validar:
  - login-server inicia
  - char-server inicia
  - map-server inicia
  - personagem consegue logar
  - job/level/rate alterado funciona no jogo
