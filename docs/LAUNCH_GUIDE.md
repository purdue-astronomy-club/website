# Launch Purdue Astronomy Club’s website

The complete website is in `/home/sam/website`. It is ready to upload and connect to GitHub Pages. The production address will be **https://purdueastro.club/**. Editing will happen at **https://app.pagescms.org/**.

This guide separates completed local implementation from the account steps that an owner must perform. No DNS or GitHub settings were changed during the build. No hosting subscription, database, or running club computer is needed.

## 1. Set up durable club ownership

The configured repository is [purdue-astronomy-club/website](https://github.com/purdue-astronomy-club/website). During the build GitHub reported:

- The repository is public and empty.
- `purdue-astronomy-club` is currently a **personal GitHub account**, rather than an organization.
- The connected GitHub account could read the repository but could not push or administer it.

Use individual officer GitHub accounts and a club-owned organization, with at least two owners and 2FA. Decide this before setting DNS. The current account owner should use [GitHub’s Move work to an organization procedure](https://docs.github.com/en/account-and-profile/how-tos/account-management/moving-your-work-to-an-organization): open account **Settings → Organizations → Move work to an organization** and follow the prompts. To keep the name `purdue-astronomy-club` for the organization, first rename the current personal account to another available name, create the organization using the original name, then move the repository into it. Alternatively choose a different organization name and transfer the repository there. Set up individual officer accounts before changing ownership, and review GitHub’s prompts carefully. Do not share one officer login between everyone.

If the final organization is still `purdue-astronomy-club`, the links in this guide work as written. If you choose a different name, use that actual name wherever this guide says `ACTUAL_OWNER`. Update the Git remote and the guide’s repository links. The website’s `purdueastro.club` address stays the same.

Create a **Website Editors** team, give it Write access to `website`, and add the officers who will maintain content. Keep owner/admin privileges limited. Branch rules must allow the Pages CMS GitHub App to write to the publishing branch. If your organization requires approved pull requests, use a separate editorial branch and documented PR approval flow; that introduces an approval step before changes become public.

## 2. Upload the source once

This is the only setup step that needs a local Git client. Routine officer editing later uses only a browser.

Sign in as a repository owner or collaborator with Write access. GitHub Desktop is an option: add `/home/sam/website` as an existing repository, review the new files, commit, then push `main`. If GitHub Desktop cannot open the initial empty repository, use the commands below from a terminal in the workspace. Authenticate using GitHub’s normal sign-in or SSH process; GitHub account passwords do not work for HTTPS Git pushes.

```bash
cd /home/sam/website
git add .
git commit -m "Build Purdue Astronomy Club website"
git push -u origin main
```

If the organization/repo changed, update the origin first:

```bash
git remote set-url origin https://github.com/ACTUAL_OWNER/website.git
```

If Git asks for a name/email for the commit, use your approved GitHub identity (a GitHub no-reply address is fine). Do not publish account tokens in files.

Upload **source files**, including hidden `.github/`, `.pages.yml`, and `.gitignore`. Do not upload `public/`, `.venv/`, `node_modules/`, or `.generated/`. The included `.gitignore` handles these automatically. A source ZIP is supplied as a backup; do not upload the ZIP as the repository’s only file.

## 3. Enable GitHub Pages

Open [repository Pages settings](https://github.com/purdue-astronomy-club/website/settings/pages).

1. Choose **Settings → Pages → Build and deployment → Source → GitHub Actions**.
2. Open the repository’s **Actions** tab. Allow Actions if GitHub asks. The “Build and deploy website” workflow runs on pushes to `main`, and can also be started with **Run workflow**.
3. Wait for the build and deployment jobs to be green. If the initial run started before Pages was enabled, rerun it from Actions.
4. Leave the production configuration’s `baseURL` as `https://purdueastro.club/`. Asset paths are designed for the custom domain; the temporary `/website/` project URL is not the final acceptance target.

The automatic sky calendar needs no API keys or extra Porkbun settings. Scheduled builds calculate phases/oppositions/seasons locally, refresh public AMS meteor forecasts at most once per UTC day, and cache the last good forecasts. GitHub supplies a short-lived deployment token. Python and the pinned Hugo version are installed by the workflow. Builds run every six hours at 00:17, 06:17, 12:17 and 18:17 UTC, refreshing announcements, upcoming events and the optional Drive gallery. The ten initial Drive photos are already included and display without a credential. Automatic Drive refreshing needs one additional Google credential secret, described in [DRIVE_GALLERY_SETUP.md](DRIVE_GALLERY_SETUP.md); it starts disabled so the site and gallery build before that connection is configured.

## 4. Verify ownership of the domain in GitHub

Do this **before** repointing the website’s DNS.

1. In the actual organization, choose **Settings → Pages → Add a domain**. Enter `purdueastro.club`.
2. Copy the exact TXT hostname and value GitHub generates. The hostname will resemble `_github-pages-challenge-ACTUAL_OWNER.purdueastro.club`.
3. In Porkbun, open **Domain Management → purdueastro.club → DNS**. Add a TXT record. Porkbun’s Host field normally takes only the part before `.purdueastro.club`, such as `_github-pages-challenge-ACTUAL_OWNER`. Use the exact value from GitHub; it cannot be prefilled in this project.
4. Return to GitHub and click **Verify** after DNS is visible. Keep the verification TXT record permanently.

If you temporarily keep a personal GitHub account, verification is under that account’s **Settings → Pages**, rather than organization settings. Verify using the owner that actually owns `website`.

## 5. Tell the repository its custom domain

In **website → Settings → Pages → Custom domain**, enter **purdueastro.club** and Save. Do this before changing web DNS. The apex address is canonical; `www` should redirect to it.

No manually maintained CNAME file is needed for this Actions deployment. The repository’s Pages settings hold the custom domain.

## 6. Change the website DNS at Porkbun

First save a screenshot/export of existing DNS records for recovery. The domain was showing a **Coming Soon** page during the build, with apex A records `192.0.79.151` and `192.0.79.166`. Replace web-hosting records rather than leaving old and new apex A records mixed together.

The domain already used Porkbun’s `curitiba`, `fortaleza`, `maceio`, and `salvador` nameservers when checked. No nameserver change is needed if those are still in place. Confirm the domain’s authoritative nameservers. If the domain uses another provider’s nameservers, changes in Porkbun’s DNS editor will not take effect until you either edit the records at that provider or switch authoritative DNS to Porkbun. If switching nameservers, copy all needed email/security records first. The build’s observed nameservers are recorded in `TEST_REPORT.md`.

In Porkbun’s DNS editor, remove conflicting parking/website records at the bare domain and `www`. Keep MX records and email/security TXT records, including the GitHub verification TXT. Remove old apex AAAA records unless you are deliberately configuring GitHub’s documented IPv6 records too. Also remove a conflicting apex ALIAS/ANAME or URL forwarding rule if present. Do not use a bulk DNS preset when other records exist.

Create these records:

| Type | Porkbun Host | Answer / Value |
|---|---|---|
| A | blank (the bare domain; `@` in DNS notation) | `185.199.108.153` |
| A | blank | `185.199.109.153` |
| A | blank | `185.199.110.153` |
| A | blank | `185.199.111.153` |
| CNAME | `www` | `ACTUAL_OWNER.github.io` |

For the existing owner name, the CNAME answer is **purdue-astronomy-club.github.io**. Use the final owner’s actual name after ownership is settled. **Do not include `https://`, `/website`, or a trailing path** in the CNAME answer. Use Porkbun’s default TTL.

Do not create a wildcard record. Keep unrelated subdomain records intact.

DNS changes may take up to 24 hours to propagate. These optional checks are for a maintainer:

```bash
dig +short A purdueastro.club
dig +short CNAME www.purdueastro.club
dig +short TXT _github-pages-challenge-ACTUAL_OWNER.purdueastro.club
curl -IL https://purdueastro.club/
curl -IL https://www.purdueastro.club/
```

The apex query should return the four GitHub A records. The `www` query should return the final owner’s `.github.io` hostname.

## 7. Turn on HTTPS

Return to **repository → Settings → Pages**. Wait for GitHub’s DNS check and certificate provisioning to finish, then enable **Enforce HTTPS**. If the control is temporarily unavailable, wait and check for conflicting A/AAAA/CNAME records before changing settings repeatedly.

Open both `https://purdueastro.club/` and `https://www.purdueastro.club/`. Confirm the second redirects to the first and both have valid certificates. Check images, styles, navigation, `/events/`, and `/calendar.ics`. The existing Coming Soon page should be gone.

## 8. Connect Pages CMS — where officers edit the website

Open **[Pages CMS](https://app.pagescms.org/)** and sign in with the officer’s authorized GitHub account. The editing app is hosted there; there is no `/admin` login to install on this site.

1. A GitHub organization owner installs/authorizes the **Pages CMS GitHub App** for the organization.
2. Scope it to **Only select repositories → website**.
3. Approve installation if the organization requires approval.
4. In Pages CMS, select the actual owner, **website**, and the **main** branch.
5. The `.pages.yml` configuration automatically creates the editing menus below. Do not replace it with an autogenerated blank config.

| CMS menu | What an officer can change |
|---|---|
| Events and Calendar | Club/joint events, times, locations, status, cover photos, signup links, descriptions |
| Automatic Sky Calendar | Automatic moon phases/oppositions/meteor forecasts/seasons; category switches, year range, hidden entries |
| Astronomy and Night Sky | Source-verified astronomical highlights |
| Calendar Months and Banner Photos | Monthly image, credit, permission, verified sky notes |
| Event Photo Albums | Ordered photo lists, per-photo descriptions/captions/credits, related event |
| Astrophotography Showcase | Processed images, photographer, permission, capture equipment; published photos also join the homepage carousel |
| Drive Gallery Settings | Automatic imports from the selected Drive folder, title/credit/alt/caption corrections, hidden photos |
| News and Announcements | Rich text, image, summary, publication date |
| Club Officers | Names, roles, portraits, biography, display order, active status; eight 2026–27 profiles are included |
| Officer Page Settings | Academic year and introduction above the officer cards |
| Sponsors and Partners | Approved acknowledgments, logos, public links, order |
| Homepage Settings | Hero headline, description, image, button text, section visibility |
| Contact and Social Links | Approved public email/social links and footer copy |
| About the Club / Contact Page | Page copy in a rich-text editor |
| Generate Monthly Calendar Graphic | Optional workflow producing downloadable PNG/PDF artifacts |

Save changes in Pages CMS. It commits to GitHub; Actions validates, builds, and deploys automatically. The CMS is a content editor, not a drag-and-drop redesign tool. The site’s underlying layout remains consistent.

To connect the supplied Google Drive folder for automatic gallery uploads, follow [Drive gallery setup](DRIVE_GALLERY_SETUP.md). Filenames such as `jane_doe_andromeda_galaxy.jpg` supply the target title and photographer credit. The folder ID is prefilled; the owner must create/share a dedicated reader account, add its JSON key as a GitHub secret, then enable the connection in CMS. No additional DNS changes are needed.

## 9. Run the owner’s final publishing test

These account-bound tests could not be done from the read-only GitHub connection:

- Sign in as a non-admin officer with Write access.
- Create an unpublished test event and save it. Confirm a GitHub commit and a successful Actions run, and that the draft is absent publicly.
- Upload a prepared, approved image. Select it in an entry, add alt text, save, and inspect the result.
- Create an album with three approved photos. Check order, captions, and credits.
- Publish one real confirmed event, then move its date in CMS. Confirm its calendar month, detail page, homepage, JSON and `.ics` update together.
- Cancel the event and check that it is marked and removed from homepage upcoming cards. Restore the correct status afterward.
- Edit the homepage introduction and a photo credit. Check that the change becomes visible after Actions finishes. Restore any test copy.
- Test image reuse/replacement. Before deleting media, remove every reference or replace the image. A referenced missing image must fail validation and preserve the previous live deployment.
- Optionally run **Generate Monthly Calendar Graphic**, enter `YYYY-MM`, then download the `monthly-calendar` artifact from the linked Actions run. Inspect PNG/PDF for readability before sharing. This uses the website data; no separate manual social calendar is required.
- Import one downloaded event `.ics` into an actual calendar app and check Indiana time. Subscribe to `/calendar.ics` if desired. Calendar apps set their own refresh delay.

Finish by adding actual club contact information, joining instructions, current officers, approved photos, and confirmed events. None were fabricated for this build. The supplied example event is deliberately Draft and is not public.

## 10. Keep it running next year

Enable Porkbun auto-renew and MFA; verify the payment method and renewal email belong to the club’s responsible administrators. Keep two current GitHub organization owners. Follow `ADMIN_HANDOFF.md` and `RECOVERY.md` when officers change. Preserve the GitHub domain-verification TXT record.

## Official setup references

Checked during implementation on October 22, 2026:

- [GitHub: configure a custom domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
- [GitHub: verify a domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages)
- [Porkbun: domain DNS controls and GitHub Pages](https://kb.porkbun.com/article/64-how-to-connect-your-domain-to-github-pages)
- [Hugo: GitHub Pages deployment](https://gohugo.io/host-and-deploy/deploy-to-github-pages/)
- [Pages CMS: configuration](https://pagescms.org/docs/configuration/), [media](https://pagescms.org/docs/configuration/media/), [actions](https://pagescms.org/docs/configuration/actions/)
