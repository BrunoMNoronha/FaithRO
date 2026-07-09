---
applyTo: "**/{scripts,infra,.github}/**/*"
---

# Instruções DevOps

- Não expor IPs, senhas, tokens ou chaves privadas.
- Scripts devem falhar cedo: `set -euo pipefail`.
- Toda automação deve ter logs.
- Para produção, sempre considerar backup, firewall, usuário não-root e rollback.
- Não usar comandos destrutivos sem confirmação explícita em documentação.
