from pathlib import Path
import sys
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'app'))
from figure_reports.chat_coordinator import main
if '--state' not in sys.argv:sys.argv.extend(['--state',str(root/'state')])
main()
