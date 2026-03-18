const fs = require('fs');
let file = '/home/lockboxpi/snapdrop/server/index.js';
let code = fs.readFileSync(file, 'utf8');
if (!code.includes("this.ip = 'lockbox'")) {
    code = code.replace(/this\.ip = '127\.0\.0\.1';\s*}/g, "this.ip = '127.0.0.1';\n        }\n        this.ip = 'lockbox';");
    fs.writeFileSync(file, code);
    console.log("Patched successfully.");
} else {
    console.log("Already patched.");
}
