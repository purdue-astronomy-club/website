# Annual administrator handoff

Record administrative responsibility in the club’s approved private records, not in public repository files. Do not record passwords, recovery codes, or personal phone numbers here.

| Responsibility | Required continuity |
|---|---|
| GitHub organization | At least two current officer owners, individual accounts, 2FA |
| Website editing | Website Editors team with Write access, scoped Pages CMS App |
| Porkbun | Two responsible club administrators where supported, MFA, accessible recovery process |
| Domain renewal | Auto-renew on, valid payment method, renewal notices checked |
| Publication | `main` deploys through Build and deploy website; watch failures |
| Content review | Events, astronomy sources, permissions, officer list, contact links reviewed |
| Drive gallery, if enabled | Club ownership of the Cloud project/folder, reader Viewer access, working GitHub credential secret and key rotation |

Before outgoing officers lose access, incoming officers must sign into GitHub and Pages CMS, save a test draft, upload an approved photo, and see the successful Actions run. Confirm at least one incoming owner can access repository Pages settings and the domain’s DNS. Review the current Pages CMS App installation and repository scope.

Give new officers the production URL, [OFFICER_GUIDE.md](OFFICER_GUIDE.md), [LAUNCH_GUIDE.md](LAUNCH_GUIDE.md), and [RECOVERY.md](RECOVERY.md). Remove departed officers’ access after the transfer is verified. Review public officer pages separately.

For the optional automatic gallery, also hand over [DRIVE_GALLERY_SETUP.md](DRIVE_GALLERY_SETUP.md), the Google Cloud project and folder administration. Rotate the service-account key, replace `DRIVE_GALLERY_CREDENTIALS_JSON` in GitHub, run a successful deployment, then revoke the previous key. Verify one permitted upload and removal. Do not hand keys around in public repository files.

Preserve the GitHub verification TXT record. Do not delete the repository or remove its Pages domain while DNS still points to GitHub; if retiring the site, change DNS away first as part of a planned shutdown.

Routine content edits require no developer. Dependency updates, template changes, CI changes, and major design work should get a maintainer review. Dependabot opens monthly dependency updates; merge them only after checks pass. Re-test calendar behavior and media after Hugo/FullCalendar/CMS upgrades.

Check that the scheduled website workflow remains enabled, especially after summer breaks. [GitHub disables scheduled workflows in public repositories after 60 days without repository activity](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). An owner can re-enable it from the Actions page and run a build. Ordinary CMS commits also rebuild the site. Review the public automatic-sky source/check-date disclosure if meteor forecasts look out of date.
