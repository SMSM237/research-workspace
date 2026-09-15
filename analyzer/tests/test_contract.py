import copy
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def report():
    return json.loads((ROOT / 'examples/demo.analysis.json').read_text(encoding='utf-8'))

def api():
    from figure_reports.validate import validate_report, ReportValidationError
    return validate_report, ReportValidationError

def test_valid_demo(report):
    validate, _ = api(); validate(report, ROOT / 'assets')

@pytest.mark.parametrize('mutation', ['source', 'concept', 'panel_missing', 'panel_duplicate', 'id_duplicate', 'coverage_target', 'coverage_missing', 'external_without_source'])
def test_broken_links_fail(report, mutation):
    validate, Error = api()
    if mutation == 'source': report['figures'][0]['observations'][0]['refs'] = ['absent']
    elif mutation == 'concept': report['figures'][0]['concept_links'][0]['concept_id'] = 'absent'
    elif mutation == 'panel_missing': report['figures'][0]['panel_groups'] = []
    elif mutation == 'panel_duplicate': report['figures'][0]['panel_groups'].append(copy.deepcopy(report['figures'][0]['panel_groups'][0]))
    elif mutation == 'id_duplicate': report['figures'][1]['id'] = report['figures'][0]['id']
    elif mutation == 'coverage_target': report['coverage'][0]['linked_to'] = ['absent']
    elif mutation == 'coverage_missing': report['coverage'].pop()
    elif mutation == 'external_without_source': report['concepts'][0]['origin'] = 'external'; report['concepts'][0]['refs'] = []
    with pytest.raises(Error): validate(report)

@pytest.mark.parametrize('path', ['../outside.png', '/tmp/out.png', 'C:\\Windows\\x.png', 'https://x.test/a.png', 'Resources/DEMO/../../x.png', 'Resources/DEMO/%2e%2e/x.png', 'Resources/OTHER/a.png'])
def test_unsafe_asset_path_fails(report, path):
    validate, Error = api(); report['figures'][0]['image']['path'] = path
    with pytest.raises(Error): validate(report)

def test_missing_asset_fails(report, tmp_path):
    validate, Error = api()
    with pytest.raises(Error): validate(report, tmp_path)

def test_real_paper_cannot_use_demo_assets(report):
    validate, Error = api(); report['kind'] = 'paper'
    with pytest.raises(Error): validate(report)

def test_symlink_escape_fails(report, tmp_path):
    validate, Error = api(); path = tmp_path / report['figures'][0]['image']['path']; path.parent.mkdir(parents=True)
    outside = tmp_path.parent / 'outside-demo.png'; outside.write_bytes(b'x')
    try:
        path.symlink_to(outside)
    except OSError as exc:
        if getattr(exc, 'winerror', None) == 1314:
            pytest.skip('Windows account lacks symbolic-link privilege; junction escape has a separate test')
        raise
    with pytest.raises(Error): validate(report, tmp_path)

def test_analyzed_source_requires_rendered_reference(report):
    validate, Error = api()
    report['sources'].append({'id':'orphan','kind':'methods','locator':'orphan','note':'not linked'})
    report['coverage'].append({'source_id':'orphan','status':'analyzed','linked_to':['fig-1'],'reason':''})
    with pytest.raises(Error): validate(report)
