"""The same build entry point locally and on GitHub Actions."""
import os
import shutil
import subprocess
from content import ROOT
from build_calendar import generate
from automatic_sky import settings
from refresh_meteors import refresh
from optimize_images import optimize
from sync_drive_gallery import sync
from validate_public_output import validate

os.chdir(ROOT)
sync()
config = settings()
if config.get('enabled') and config.get('meteor_showers',True) and not os.environ.get('PAC_OFFLINE'):
    refresh()
generate()
optimize()
subprocess.run([os.environ.get('HUGO_BIN', 'hugo'), '--gc', '--minify', '--cleanDestinationDir'], check=True)
if (ROOT/'.generated/uploads').exists():
    shutil.copytree(ROOT/'.generated/uploads', ROOT/'public/uploads', dirs_exist_ok=True)
validate(ROOT/'public')
