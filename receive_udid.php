<?php
/**
 * lockboxPRO - Enrollment & UDID Capture
 * Path: /var/www/dumps/receive_udid.php
 */

$data = file_get_contents('php://input');

file_put_contents('enrollment_debug.log', date('Y-m-d H:i:s') . " - Request Received\n", FILE_APPEND);

if (empty($data)) {
    header('HTTP/1.1 200 OK');
    echo "lockboxPRO Node Active. Waiting for enrollment...";
    exit;
}

preg_match('/<key>UDID<\/key>\s*<string>(.*?)<\/string>/', $data, $matches);
$udid = $matches[1] ?? null;

if ($udid) {
    file_put_contents('last_enrolled_udid.txt', $udid);
    file_put_contents('enrollment_debug.log', "Captured UDID: $udid\n", FILE_APPEND);

    // --- TELEGRAM BOT NOTIFICATION ---
    $envPath = '/home/lockboxpi/.env';
    if (file_exists($envPath)) {
                $envContent = file_get_contents($envPath);
        preg_match('/BOT_TOKEN=(.*)/', $envContent, $tokenMatch);
        preg_match('/ALLOWED_USERS=(.*)/', $envContent, $usersMatch);
        
        if (isset($tokenMatch[1]) && isset($usersMatch[1])) {
            $botToken = trim($tokenMatch[1]);
            $chatIds = explode(',', trim($usersMatch[1]));
                        // Always send to the main admin (the first ID in ALLOWED_USERS)
            $adminId = trim($chatIds[0]);
            $targetChats = [$adminId];
            
            // Also explicitly add the group chat ID the user requested
            $groupChat = "-1003707368771";
            if (!in_array($groupChat, $targetChats)) {
                $targetChats[] = $groupChat;
            }

            foreach ($targetChats as $chatId) {
                if ($botToken && $chatId) {
                    $msg = "📱 <b>New iPhone Linked!</b>\n\n<b>UDID:</b> <code>$udid</code>";
                    $url = "https://api.telegram.org/bot$botToken/sendMessage";
                    $postData = json_encode(['chat_id' => $chatId, 'text' => $msg, 'parse_mode' => 'HTML']);
                    $ch = curl_init($url);
                    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                    curl_setopt($ch, CURLOPT_POST, true);
                    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
                    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
                    $result = curl_exec($ch);
                    if ($result === false) {
                        file_put_contents('enrollment_debug.log', "Telegram API Error for $chatId: " . curl_error($ch) . "\n", FILE_APPEND);
                    } else {
                        file_put_contents('enrollment_debug.log', "Telegram Response for $chatId: $result\n", FILE_APPEND);
                    }
                    curl_close($ch);
                }
            }
        } else {
            file_put_contents('enrollment_debug.log', "Missing keys in .env\n", FILE_APPEND);
        }
    } else {
        file_put_contents('enrollment_debug.log', "Could not find .env file at $envPath\n", FILE_APPEND);
    }
    // ---------------------------------

    // 4. THE CRITICAL HANDOFF
    header('HTTP/1.1 301 Moved Permanently');
    header('Location: https://lbpi.jessejesse.com/dumps/success_enroll.html');
    exit;

} else {
    file_put_contents('enrollment_debug.log', "FAILED: No UDID found in POST data.\n", FILE_APPEND);
    header('HTTP/1.1 400 Bad Request');
    echo "Error: Could not parse UDID.";
}
?>
