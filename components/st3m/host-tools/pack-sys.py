import glob
import io
import os
import sys
import tarfile
import zlib

from typing import List, Set


class SysFile:
    def __init__(self, path_local: str, path_tar: str) -> None:
        self._local = path_local
        self._tar = path_tar

    def __repr__(self) -> str:
        return f'<SysFile {self._tar} -> {self._local}>'


def _prepare_filelist(root: str) -> List[SysFile]:
    paths = glob.glob(os.path.join(root, "**", "*"), recursive=True)

    res = []
    seen: Set[str] = set()
    for g in paths:
        if g in seen:
            continue
        seen.add(g)

        if not os.path.isfile(g):
            continue

        parts = g.split(os.path.sep)
        print(g)
        if '__pycache__' in parts:
            continue
        if 'mypystubs' in parts:
            continue

        tarpath = os.path.relpath(g, root)
        res.append(SysFile(g, tarpath))

    return res


def main() -> int:
    if len(sys.argv) != 3:
        sys.stderr.write(f"Usage: {sys.argv[0]} sys_directory out.c\n")
        return 1

    sysdir = sys.argv[1]
    outfile = sys.argv[2]

    if not os.path.isdir(sysdir):
        sys.stderr.write(f"First argument must be a directory")
        return 1

    # Build tar.
    filelist = _prepare_filelist(sysdir)
    fobj = io.BytesIO()
    tar = tarfile.TarFile(fileobj=fobj, mode='w', dereference=True)
    for sf in filelist:
        tar.add(sf._local, arcname=sf._tar)

    z = zlib.compress(fobj.getvalue())

    with open(outfile, 'w') as f:
        f.write('// Generated by pack-sys.py. Do not edit.\n')
        f.write('#include <stddef.h>\n')
        f.write('#include <stdint.h>\n')
        f.write('\n')
        f.write('// zlib-compressed python_payload tarball.\n')
        f.write('const size_t st3m_sys_data_length = {};\n'.format(len(z)))
        f.write('const uint8_t st3m_sys_data[] = {\n')
        while len(z) > 0:
            chunk, z = z[:16], z[16:]
            f.write('    ')
            f.write(', '.join(f'0x{b:02x}' for b in chunk))
            f.write(',\n')
        f.write('};\n')

    return 0

if __name__ == '__main__':
    sys.exit(main() or 0)
