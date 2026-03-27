<?php
$file = '/dumps/receive_udid.php';
$content = file_get_contents($file);

$newLoop = <<<EOT
            // Always send to the main admin (the first ID in ALLOWED_USERS)
            \$adminId = trim(\$chatIds[0]);
            \$targetChats = [\$adminId];
            
            // Also explicitly add the group chat ID the user requested
            \$groupChat = "-1003707368771";
            if (!in_array(\$groupChat, \$targetChats)) {
                \$targetChats[] = \$groupChat;
            }

            foreach (\$targetChats as \$chatId) {
                if (\$botToken && \$chatId) {
                    \$msg = "📱 <b>New iPhone Linked!</b>\\n\\n<b>UDID:</b> <code>\$udid</code>";
                    \$url = "https://api.telegram.org/bot\$botToken/sendMessage";
                    \$postData = json_encode(['chat_id' => \$chatId, 'text' => \$msg, 'parse_mode' => 'HTML']);
                    \$ch = curl_init(\$url);
                    curl_setopt(\$ch, CURLOPT_RETURNTRANSFER, true);
                    curl_setopt(\$ch, CURLOPT_POST, true);
                    curl_setopt(\$ch, CURLOPT_POSTFIELDS, \$postData);
                    curl_setopt(\$ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
                    \$result = curl_exec(\$ch);
                    if (\$result === false) {
                        file_put_contents('enrollment_debug.log', "Telegram API Error for \$chatId: " . curl_error(\$ch) . "\\n", FILE_APPEND);
                    } else {
                        file_put_contents('enrollment_debug.log', "Telegram Response for \$chatId: \$result\\n", FILE_APPEND);
                    }
                    curl_close(\$ch);
                }
            }
EOT;

$content = preg_replace(
    '/\$chatId = trim\(\$chatIds\[0\]\);.*?curl_close\(\$ch\);\s*\}/s',
    $newLoop,
    $content
);

file_put_contents($file, $content);
echo "Patched group loop";
