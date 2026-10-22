const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
 testDir:'tests/e2e', fullyParallel:true,
 use:{baseURL:'http://127.0.0.1:1313'},
 projects:[{name:'chromium',use:{browserName:'chromium'}},{name:'firefox',use:{browserName:'firefox'}}],
 webServer:{command:'python3 -m http.server 1313 --bind 127.0.0.1 --directory public',url:'http://127.0.0.1:1313',reuseExistingServer:!process.env.CI},
 reporter:'list'
});
