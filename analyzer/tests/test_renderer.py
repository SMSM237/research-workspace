import json
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def report():
    return json.loads((ROOT / 'examples/demo.analysis.json').read_text(encoding='utf-8'))

def test_markdown_deterministic(report):
    from figure_reports.render import render_markdown
    assert render_markdown(report) == render_markdown(report)

def test_all_concept_details_and_critical_caveats_present(report):
    from figure_reports.render import render_markdown, render_html
    md = render_markdown(report); html = render_html(report, ROOT / 'assets')
    for c in report['concepts']:
        assert c['definition'] in md and c['definition'] in html
        for p in c['details']: assert p in md and p in html
    for f in report['figures']:
        for limitation in f['limitations']:
            assert limitation['text'] in md and limitation['text'] in html
    assert 'data-critical="true"' in html

def test_figure_panel_source_coverage_rendered(report):
    from figure_reports.render import render_markdown
    md = render_markdown(report)
    for fig in report['figures']:
        assert fig['label'] in md
        for group in fig['panel_groups']: assert group['reading'] in md
    for source in report['sources']: assert source['locator'] in md

def test_script_like_text_is_never_executable(report):
    from figure_reports.render import render_html
    report['paper']['title'] = '<script>alert("XSS")</script>'
    html = render_html(report, ROOT / 'assets')
    assert '<script>alert("XSS")</script>' not in html
    assert '&lt;script&gt;' in html

def test_preview_is_self_contained(report):
    from figure_reports.render import render_html
    html = render_html(report, ROOT / 'assets')
    assert 'data:image/png;base64,' in html
    assert '<script src=' not in html and '<link rel="stylesheet"' not in html

def test_build_nomedia_relative_images_and_no_note_changes(report, tmp_path):
    from figure_reports.build import build_report
    note = tmp_path / 'Notes' / 'DEMO.md'; note.parent.mkdir(); note.write_text('MY NOTES')
    paths = build_report(report, ROOT / 'assets', tmp_path)
    assert (tmp_path / 'Resources/.nomedia').exists()
    assert (tmp_path / 'Paper reports/DEMO.md').exists()
    md = (tmp_path / 'Paper reports/DEMO.md').read_text(encoding='utf-8')
    assert '../Resources/DEMO/Fig01.png' in md
    assert note.read_text(encoding='utf-8') == 'MY NOTES'
    assert paths['markdown'] == 'Paper reports/DEMO.md'

def test_managed_user_edit_is_protected(report, tmp_path):
    from figure_reports.build import build_report, ModifiedOutputError
    build_report(report, ROOT / 'assets', tmp_path)
    out = tmp_path / 'Paper reports/DEMO.md'; out.write_text('USER EDIT', encoding='utf-8')
    with pytest.raises(ModifiedOutputError): build_report(report, ROOT / 'assets', tmp_path)
    assert out.read_text(encoding='utf-8') == 'USER EDIT'

def test_output_symlink_escape_is_protected(report, tmp_path):
    from figure_reports.build import build_report
    outside=tmp_path.parent/'outside-output'; outside.mkdir(exist_ok=True)
    try:
        (tmp_path/'Resources').symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        if getattr(exc, 'winerror', None) == 1314:
            pytest.skip('Windows account lacks symbolic-link privilege; junction escape has a separate test')
        raise
    with pytest.raises((ValueError, OSError)): build_report(report, ROOT / 'assets', tmp_path)

def test_missing_asset_does_not_publish_partial_report(report, tmp_path):
    from figure_reports.build import build_report
    with pytest.raises(ValueError): build_report(report, tmp_path / 'absent', tmp_path / 'out')
    assert not (tmp_path / 'out/Paper reports/DEMO.md').exists()

def test_every_internal_preview_link_resolves(report):
    import re
    from figure_reports.render import render_html
    html=render_html(report, ROOT / 'assets')
    ids=set(re.findall(r'\bid="([^"]+)"',html))
    targets=set(re.findall(r'href="#([^"]+)"',html))
    assert not targets-ids


def test_standalone_table_image_export_and_missing_asset(report, tmp_path):
    import copy, shutil
    from figure_reports.build import build_report
    from figure_reports.render import render_markdown, render_html
    from figure_reports.validate import validate_report, ReportValidationError
    before=render_markdown(report)
    image=copy.deepcopy(report['figures'][0]['image'])
    image['path']='Resources/DEMO/Table1.png'
    entry=report['standalone'][0] if report['standalone'] else None
    if entry is None:
        entry={'id':'table-1','title':'Table 1','blocks':[{'text':'Original interpretation','refs':[]}]}
        report['standalone'].append(entry)
    entry['image']=image
    assets=tmp_path/'assets';shutil.copytree(ROOT/'assets',assets)
    shutil.copy2(assets/report['figures'][0]['image']['path'],assets/image['path'])
    validate_report(report,assets)
    md=render_markdown(report)
    assert md.index('![',md.index('### 독립 근거')) < md.index(entry['blocks'][0]['text'],md.index('### 독립 근거'))
    assert '../Resources/DEMO/Table1.png' in md
    assert 'data:image/png;base64,' in render_html(report,assets)
    output=tmp_path/'vault';build_report(report,assets,output)
    assert (output/image['path']).read_bytes()==(assets/image['path']).read_bytes()
    assert (output/'Resources/.nomedia').exists()
    (assets/image['path']).unlink()
    with pytest.raises(ReportValidationError):validate_report(report,assets)
    image['path']='Resources/DEMO/../outside.png'
    with pytest.raises(ReportValidationError):validate_report(report)
