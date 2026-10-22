# Recover content or a broken deployment

A failed build keeps the last successful GitHub Pages deployment online. Start with the red workflow log; do not change DNS to fix a content-validation failure.

## Correct a field

Open the affected entry in Pages CMS, fix the field named in the Actions error, and Save. A new successful build publishes the correction.

## Restore an older file through GitHub

A repository maintainer can open the file on GitHub → History → choose a known-good commit → view the file at that commit. Copy the prior content, return to the current file, choose Edit, replace it with that known-good version, and commit. Restore an accidentally removed image from the earlier commit too. Retain its original path, or update every reference.

For a change spanning multiple files, a maintainer should revert the content commit on a branch and open a pull request. Avoid force-pushing history. Review and merge the recovery; Actions rebuilds from the restored source.

A CMS Draft prevents a content page from publishing, but uploaded media and Git history remain public. If private data was uploaded accidentally, contact the club’s repository administrator promptly; removing it from the current page does not remove it from public Git history.

## Rebuild from a fresh clone

Install Hugo extended **0.168.0**, Python **3.12+**, and the packages in `requirements-ci.txt`. Run `python scripts/build.py`. Generated feeds and images are recreated; no live database or other club server is needed. README contains exact commands. Restore source from GitHub or the delivered source ZIP if needed.

## Domain issues

Use the DNS table in LAUNCH_GUIDE. Confirm Porkbun nameservers, the four apex GitHub A records, `www` CNAME, verification TXT, repository custom domain, and Enforce HTTPS. Preserve email/security records. If reverting to the old hosting provider, use the prelaunch DNS screenshot/export instead of guessing its records.
