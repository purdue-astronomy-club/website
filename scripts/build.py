"""The same build entry point locally and on GitHub Actions."""
import os
import subprocess
from content import ROOT
from build_calendar import generate
from automatic_sky import settings
from refresh_meteors import refresh
from optimize_images import optimize
from sync_drive_gallery import sync
from validate_public_output import validate
from site_config import base_url

os.chdir(ROOT)
sync()
config = settings()
if config.get('enabled') and config.get('meteor_showers',True) and not os.environ.get('PAC_OFFLINE'):
    refresh()
optimize()
generate()
subprocess.run([os.environ.get('HUGO_BIN', 'hugo'), '--gc', '--minify', '--cleanDestinationDir', '--baseURL', base_url()], check=True)
validate(ROOT/'public')
