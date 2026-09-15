import json
import sys
import threading
from pathlib import Path
import pytest
from figure_reports.model_adapter import CodexSubscription,require_consent,subscription_environment

SCHEMA={'type':'object','properties':{'readable':{'type':'boolean'}},'required':['readable'],'additionalProperties':False}

def setup(tmp_path, behavior='ok',login='ChatGPT'):
    exe=tmp_path/'fake_codex.py'
    exe.write_text(f'''import sys,json,time
from pathlib import Path
if sys.argv[1:3]==['login','status']:
    print('Logged in using {login}');sys.exit(0)
prompt=sys.stdin.read()
if {behavior!r}=='slow':time.sleep(20)
value='not json' if {behavior!r}=='bad' else json.dumps({{'readable':True}})
Path(sys.argv[sys.argv.index('-o')+1]).write_text(value)
print(json.dumps({{'type':'turn.completed','usage':{{'input_tokens':1}}}}))
''',encoding='utf-8')
    backend=CodexSubscription(sys.executable,timeout=.1 if behavior=='slow' else 5)
    backend.command=[sys.executable,str(exe)]
    job=dict(allow_model_upload=True,fingerprint='fixed',source_hashes=['sha'])
    consent=dict(destination='codex-openai-chatgpt',auth_method='chatgpt',fingerprint='fixed',source_hashes=['sha'],user_approved=True)
    return backend,job,consent

def test_subscription_only_environment_and_arguments(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','sentinel');monkeypatch.setenv('CODEX_API_KEY','sentinel')
    assert 'OPENAI_API_KEY' not in subscription_environment() and 'CODEX_API_KEY' not in subscription_environment()
    b,j,c=setup(tmp_path)
    args=b.arguments(tmp_path/'result',tmp_path/'schema',[])
    assert 'forced_login_method="chatgpt"' in args and 'read-only' in args and 'shell_tool' in args

def test_missing_or_mismatched_consent_blocks_before_subprocess(tmp_path):
    b,j,c=setup(tmp_path);c['fingerprint']='other'
    with pytest.raises(PermissionError):b.run(j,c,'',[],SCHEMA,tmp_path/'output')
    assert not (tmp_path/'output').exists()

def test_api_login_is_rejected_without_fallback(tmp_path):
    b,j,c=setup(tmp_path,login='API key')
    with pytest.raises(PermissionError):b.run(j,c,'',[],SCHEMA,tmp_path/'output')

def test_success_cache_resume_and_changed_request(tmp_path):
    b,j,c=setup(tmp_path);out=tmp_path/'output';assert b.run(j,c,'paper',[],SCHEMA,out)=={'readable':True}
    b.command=['nonexistent'];assert b.run(j,c,'paper',[],SCHEMA,out)=={'readable':True}
    with pytest.raises(ValueError):b.run(j,c,'changed',[],SCHEMA,out)
    (out/'validated.json').write_text('{}')
    with pytest.raises(ValueError):b.run(j,c,'paper',[],SCHEMA,out)

def test_invalid_json_is_not_a_completed_checkpoint(tmp_path):
    b,j,c=setup(tmp_path,behavior='bad');out=tmp_path/'output'
    with pytest.raises(ValueError):b.run(j,c,'',[],SCHEMA,out)
    assert json.loads((out/'request-record.json').read_text())['status']=='failed'
    assert not (out/'validated.json').exists()

def test_timeout_terminates_owned_request_and_keeps_failure(tmp_path):
    b,j,c=setup(tmp_path,behavior='slow');out=tmp_path/'output'
    with pytest.raises(TimeoutError):b.run(j,c,'',[],SCHEMA,out)
    assert json.loads((out/'request-record.json').read_text())['status']=='failed'

def test_cancel_before_request_does_not_upload(tmp_path):
    b,j,c=setup(tmp_path);stop=threading.Event();stop.set()
    with pytest.raises(InterruptedError):b.run(j,c,'',[],SCHEMA,tmp_path/'output',stop)


@pytest.mark.skipif(sys.platform!='win32',reason='Windows console behavior')
def test_auth_and_analysis_subprocesses_do_not_create_windows(tmp_path,monkeypatch):
    import subprocess
    calls=[];original=subprocess.Popen
    def capture(*args,**kwargs):
        calls.append(kwargs.get('creationflags',0))
        return original(*args,**kwargs)
    monkeypatch.setattr(subprocess,'Popen',capture)
    b,j,c=setup(tmp_path);b.run(j,c,'',[],SCHEMA,tmp_path/'output')
    assert len(calls)==2
    assert all(flags & subprocess.CREATE_NO_WINDOW for flags in calls)

def test_usage_limit_recognition_does_not_treat_scientific_errors_as_quota():
    from figure_reports.model_adapter import subscription_limit_message
    assert subscription_limit_message(["You've hit your usage limit. Try again later."])
    assert subscription_limit_message(['rate_limit_exceeded'])
    assert not subscription_limit_message(['invalid source quotation'])


def test_capacity_and_auth_failures_are_account_wide_not_paper_errors():
    from figure_reports.model_adapter import provider_block, SubscriptionAuthError, ProviderCapacityError
    assert isinstance(provider_block(['Selected model is at capacity. Please try a different model.']),ProviderCapacityError)
    assert isinstance(provider_block(['Token refresh failed: please sign in again']),SubscriptionAuthError)
    assert provider_block(['invalid source quotation']) is None

def test_missing_login_has_typed_error_and_no_request_upload(tmp_path):
    from figure_reports.model_adapter import SubscriptionAuthError
    b,j,c=setup(tmp_path,login='API key')
    with pytest.raises(SubscriptionAuthError):b.run(j,c,'',[],SCHEMA,tmp_path/'out')
    assert not list((tmp_path/'out').glob('attempt-*'))


def test_runner_identity_guard_rejects_sandbox_and_allows_expected_user(monkeypatch):
    from figure_reports import model_adapter as m
    monkeypatch.setattr(m,'windows_user',lambda:'CodexSandboxOffline')
    with pytest.raises(m.SubscriptionAuthError):m.require_runner_user('sampleuser')
    monkeypatch.setattr(m,'windows_user',lambda:'SAMPLEUSER')
    m.require_runner_user('sampleuser')
