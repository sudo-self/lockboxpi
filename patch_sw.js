const fs = require('fs');
let file = '/home/lockboxpi/snapdrop/client/scripts/ui.js';
let code = fs.readFileSync(file, 'utf8');
if (code.includes("navigator.serviceWorker.register('service-worker.js')")) {
    code = code.replace(/navigator\.serviceWorker\.register\('service-worker\.js'\)/g, "// navigator.serviceWorker.register('service-worker.js')");
    fs.writeFileSync(file, code);
    console.log("Service Worker disabled successfully.");
} else {
    console.log("Service Worker already disabled or not found.");
}
