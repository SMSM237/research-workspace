import importlib.util,json
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('installer',Path(__file__).parents[1]/'install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

def test_fresh_install_preserves_private_settings_and_watch_only(tmp_path):
    vault=tmp_path/'vault';(vault/'.obsidian').mkdir(parents=True)
    dest=tmp_path/'analyzer'
    result=installer.install(vault,dest,'https://github.com/example/private-vault.git',True)
    assert json.loads((dest/'config.json').read_text('utf-8'))==result
    assert result['auto_publish'] is False and 'model_executable' not in result
    assert (dest/'state/analysis-hold.json').exists()
    assert json.loads((dest/'mobile-control.json').read_text())['enabled'] is False
    assert (dest/'app/figure_reports/resources/chat-analysis-prompt.md').exists()
    before=(dest/'config.json').read_bytes()
    with pytest.raises(FileExistsError):installer.install(vault,dest,'',True)
    assert (dest/'config.json').read_bytes()==before
    assert not list(vault.rglob('config.json'))

def test_installer_refuses_wrong_root_synced_settings_and_embedded_credentials(tmp_path):
    vault=tmp_path/'vault';vault.mkdir()
    with pytest.raises(ValueError):installer.install(vault,tmp_path/'bad','',True)
    (vault/'.obsidian').mkdir()
    with pytest.raises(ValueError):installer.install(vault,vault/'app','',True)
    with pytest.raises(ValueError):installer.install(vault,tmp_path/'secret','https://token@github.com/example/vault',True)
    assert not (tmp_path/'secret').exists()

def test_inbox_detects_multiple_pdfs_while_ai_is_held(tmp_path):
    import fitz
    from figure_reports.worker_runtime import LocalWorker
    vault=tmp_path/'vault';(vault/'.obsidian').mkdir(parents=True);(vault/'Inbox').mkdir()
    dest=tmp_path/'analyzer';installer.install(vault,dest,'',True)
    for n in range(2):
        doc=fitz.open();page=doc.new_page();page.insert_text((30,50),f'Synthetic paper {n}');doc.save(vault/'Inbox'/f'demo-{n}.pdf');doc.close()
    worker=LocalWorker(vault,dest/'state',stable_seconds=0)
    worker.scan_inbox(now=0);worker.scan_inbox(now=1);worker.tick()
    first=worker.queue.list();assert len(first)==2
    worker.tick();assert len(worker.queue.list())==2
    assert all(j['state']!='complete' for j in first)
    assert not list((vault/'Paper reports').glob('*.md')) if (vault/'Paper reports').exists() else True
