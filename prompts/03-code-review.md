# Prompt - Revisão de PR

Revise este PR do FaithRO.

Contexto:
- rAthena.
- Old school/high rate.
- Sem 3ª classes.
- Base level máximo planejado 255; atributo/status natural máximo individual
  planejado 185; ASPD máxima planejada 197; job level máximo pendente por
  classe.
- Esses valores são estado-alvo e ainda dependem de implantação e validação;
  não presuma que já estão implantados.
- Sem pay-to-win.

Analise:
- Segurança.
- Estabilidade.
- Compatibilidade com upstream.
- Risco de quebrar login/char/map.
- Configuração de base level (limite 255).
- Limite natural individual de atributos (185) e clamps corretos.
- ASPD máxima (197): clamp correto e distinção entre AGI, ASPD e delays de
  skills.
- Tipos numéricos e limites internos do emulador.
- Interfaces (exibição de level, atributos e ASPD em valores altos).
- Uso preferencial de `conf/import` e `db/import`; nenhuma alteração no core
  quando um override/config resolver.
- Risco de economia/balanceamento.
- Segredos acidentais.
- Necessidade de documentação.
- Testes descritos.
- Riscos registrados.
- Plano de rollback.

Responda com:
- Aprovar / Solicitar mudanças.
- Comentários bloqueantes.
- Comentários não-bloqueantes.
- Testes adicionais.
