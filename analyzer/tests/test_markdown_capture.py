import importlib.util
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_markdown_capture_module_exists():
    assert (ROOT/'scripts/capture_markdown.py').exists()

def test_capture_reads_md_not_report_json(tmp_path):
    from figure_reports.build import build_report
    import json
    build_report(json.loads((ROOT/'examples/demo.analysis.json').read_text('utf-8')),ROOT/'assets',tmp_path/'DemoVault')
    spec=importlib.util.spec_from_file_location('capture_markdown',ROOT/'scripts/capture_markdown.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    html=module.render_markdown_preview(tmp_path/'DemoVault/Papers/DEMO.md',ROOT.parent/'dashboard/plugin')
    assert 'Markdown 렌더링' in html and 'Obsidian 앱' in html
    assert 'data-callout="rr-supplement"' in html
    assert 'data:image/png;base64,' in html
    assert '연결해서 읽기 · Figure S1' not in html
    assert '<script src=' not in html and '<link rel=' not in html
    assert 'figure-first-report' in html
