# -*- coding: utf-8 -*-
"""
Reusable SHA-256 Checksum Writer and Verifier
Part of cognitive_task_pilot_skill

  python verify_battery_template.py <dir>           # 對照既有 SHA256SUMS.txt；不符即 exit 1
  python verify_battery_template.py <dir> --write   # 重新分析後才用：重寫清單

舊版每次先重寫再比對自己，永遠不會失敗；現在預設只驗證。
"""
from pathlib import Path
import hashlib, sys


def digest(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main(target, write=False):
    out = Path(target)
    if not out.exists():
        sys.exit(f'{out} does not exist')
    sums = out / 'SHA256SUMS.txt'
    current = {p.relative_to(out).as_posix(): digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS.txt'}
    if write:
        sums.write_text(''.join(f'{d}  {rel}\n' for rel, d in current.items()), encoding='utf-8')
        print(f'Wrote {len(current)} checksums -> {sums}')
        return
    if not sums.exists():
        sys.exit(f'{sums} 不存在；先執行 --write')
    recorded = dict(reversed(line.split('  ', 1)) for line in sums.read_text(encoding='utf-8').splitlines() if line.strip())
    bad = [rel for rel, d in recorded.items() if current.get(rel) != d]
    extra = sorted(set(current) - set(recorded))
    if bad or extra:
        print('Mismatch:', bad[:20], 'Unlisted:', extra[:20])
        sys.exit(1)
    print(f'Verified {len(recorded)} files.')


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--write']
    main(args[0] if args else 'output/battery-pilot-10', write='--write' in sys.argv)
