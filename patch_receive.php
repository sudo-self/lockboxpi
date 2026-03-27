<?php
$file = '/var/www/dumps/receive_udid.php';
$content = file_get_contents($file);

// Remove the injected code first
$content = preg_replace('/\/\/ --- TELEGRAM BOT NOTIFICATION ---.*?\/\/ ---------------------------------/s', '', $content);

$injection = <<<EOT
    // --- TELEGRAM BOT NOTIFICATION ---
    \$envPath = '/home/lockboxpi/.env';
    if (file_exists(\$envPath)) {
        \$envVars = parse_ini_file(\$envPath);
        if (isset(\$envVars['BOT_TOKEN']) && isset(\$envVars['ALLOWED_USERS'])) {
            \$botToken = \$envVars['BOT_TOKEN'];
            \$chatIds = explode(',', \$envVars['ALLOWED_USERS']);
            \$chatId = trim(\$chatIds[0]);
            if (\$botToken && \$chatId) {
                \$msg = "📱 <b>New iPhone Linked!</b>\\n\\n<b>UDID:</b> <code>\$udid</code>\\n\\nAltServer has been updated and restarted with this new UDID.";
                \$url = "https://api.telegram.org/bot\$botToken/sendMessage";
                \$postData = json_encode(['chat_id' => \$chatId, 'text' => \$msg, 'parse_mode' => 'HTML']);
                \$ch = curl_init(\$url);
                curl_setopt(\$ch, CURLOPT_RETURNTRANSFER, true);
                curl_setopt(\$ch, CURLOPT_POST, true);
                curl_setopt(\$ch, CURLOPT_POSTFIELDS, \$postData);
                curl_setopt(\$ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
                curl_exec(\$ch);
                curl_close(\$ch);
            }
        }
    }
    // ---------------------------------
EOT;

$content = str_replace(
    "file_put_contents('enrollment_debug.log', \"Captured UDID: \$udid\\n\", FILE_APPEND);",
    "file_put_contents('enrollment_debug.log', \"Captured UDID: \$udid\\n\", FILE_APPEND);\n\n$injection",
    $content
);

file_put_contents($file, $content);
echo "Patched successfully 2";
