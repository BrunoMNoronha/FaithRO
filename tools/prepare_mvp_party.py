"""Create one pending MVP-party sheet locally, without overwriting any file."""
import argparse
import json
from pathlib import Path
import sys

import analyze_balance_mvp as mvp


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=int, choices=mvp.TARGETS, required=True)
    parser.add_argument('--support', choices=('solo', *mvp.SUPPORTS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data = mvp.template(args.target, None if args.support == 'solo' else args.support)
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    except (OSError, ValueError) as error:
        print('Ficha não criada: ' + str(error), file=sys.stderr)
        return 2
    print('Ficha pendente criada; nenhum combate executado.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
