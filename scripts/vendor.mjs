import { copyFileSync } from 'node:fs';
copyFileSync('node_modules/fullcalendar/index.global.min.js', 'static/vendor/fullcalendar-6.1.20.min.js');
copyFileSync('node_modules/fullcalendar/LICENSE.md', 'static/vendor/FULLCALENDAR-LICENSE.md');
