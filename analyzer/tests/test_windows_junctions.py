"""Exercise real Windows reparse-point escapes without developer mode."""
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != 'nt', reason='NTFS junctions are Windows-specific')


@pytest.mark.parametrize('operation', ['validate', 'build'])
def test_junction_escape_rejected(tmp_path, operation):
    from figure_reports.validate import validate_report
    from figure_reports.build import build_report
    report = json.loads((ROOT/'examples/demo.analysis.json').read_text(encoding='utf-8'))
    outside = tmp_path/'outside'; outside.mkdir()
    sandbox = tmp_path/'vault'; sandbox.mkdir()
    link = sandbox/'Resources'
    result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(link), str(outside)], capture_output=True)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    assert link.resolve() == outside.resolve()
    try:
        if operation == 'validate':
            (outside/'DEMO').mkdir()
            (outside/'DEMO/Fig01.png').write_bytes(b'outside sentinel')
            with pytest.raises(ValueError):
                validate_report(report, sandbox)
        else:
            with pytest.raises((ValueError, OSError)):
                build_report(report, ROOT/'assets', sandbox)
            assert not list(outside.iterdir())
    finally:
        # Remove only the verified junction itself, never its target recursively.
        assert link.resolve() == outside.resolve()
        link.rmdir()
