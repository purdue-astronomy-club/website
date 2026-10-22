# Accessibility implementation and verification

The site uses semantic landmarks, one main heading per page, a skip link, visible keyboard focus, labelled navigation, and reduced-motion support. Buttons use touch-friendly dimensions. Image descriptions and credits are editable. Calendar categories have words as well as colors.

Mobile calendars default to an agenda. Without JavaScript, navigation remains visible and all published calendar entries remain in a server-rendered agenda with working detail links. Uploaded images have responsive derivatives, explicit dimensions, and lazy loading below the fold. Photo links work directly without JavaScript; the optional dialog supports Escape and returns focus to its opener.

Chromium and Firefox automated checks cover the six main routes with axe WCAG A/AA rules, responsive widths 360/390/768/1024/1440/1920, keyboard menu, no-JavaScript fallback, and calendar controls. See TEST_REPORT for the actual result. Automated checks do not establish complete WCAG conformance. A human screen-reader review and real calendar-client imports remain recommended launch acceptance steps.

Report accessibility issues through the public Contact page once officers add their approved contact details. Editors should review headings, link wording, and image descriptions each time they publish content.
