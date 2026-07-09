# Decisão técnica inicial

## Recomendação

Usar **rAthena** como emulador inicial.

## Motivos

- Comunidade grande.
- Documentação e exemplos amplos.
- Boa base para customizações comuns de servidor privado.
- Requisitos compatíveis com a VPS inicial.
- Facilidade relativa para scripts, configs e ajustes high rate.

## Alternativa

**Hercules** é uma opção sólida, especialmente se o projeto priorizar arquitetura modular/plugin-based e maior controle de baixo nível. Pode ser avaliado futuramente, mas não é a melhor escolha inicial se o objetivo é subir um MVP com rapidez e estabilidade operacional.

## Decisão

- Fase 1: rAthena.
- Fase 2: validar performance e manutenção.
- Fase 3: reavaliar Hercules apenas se houver dor real.

## Estratégia de repositório

Opção recomendada:

```text
faithro/
├─ emulator/            # fork/submodule do rAthena, se adotado
├─ custom/              # configs, NPCs, SQLs e documentação FaithRO
├─ docs/
└─ scripts/
```

Não misture segredos, dumps reais e arquivos proprietários no repositório.
