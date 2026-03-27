<?php
/**
 * lockboxPRO - Enrollment & UDID Capture
 * Path: /home/lockboxpi/dumps/receive_udid.php
 */

// Define absolute paths to prevent "file not found" errors
$basePath = '/home/lockboxpi/dumps/';
$debugLog = $basePath . 'enrollment_debug.log';
$udidFile = $basePath . 'last_enrolled_udid.txt';
$envPath  = '/home/lockboxpi/.env';

// 1. Capture the payload from the iPhone
$data = file_get_contents('php://input');

file_put_contents($debugLog, date('Y-m-d H:i:s') . " - Request Received\n", FILE_APPEND);

// If hit via browser, show status
if (empty($data)) {
    header('HTTP/1.1 200 OK');
    echo "lockboxPRO Node Active. Waiting for enrollment...";
    exit;
}

// 2. Parse the UDID from the XML plist
preg_match('/<key>UDID<\/key>\s*<string>(.*?)<\/string>/', $data, $matches);
$udid = $matches[1] ?? null;

if ($udid) {
    // Save locally for the success page to fetch
    file_put_contents($udidFile, $udid);
    file_put_contents($debugLog, "Captured UDID: $udid\n", FILE_APPEND);

    // --- TELEGRAM BOT NOTIFICATION ---
    if (file_exists($envPath)) {
        $envContent = file_get_contents($envPath);
        preg_match('/BOT_TOKEN=(.*)/', $envContent, $tokenMatch);
        preg_match('/ALLOWED_USERS=(.*)/', $envContent, $usersMatch);
        
        if (isset($tokenMatch[1]) && isset($usersMatch[1])) {
            $botToken = trim($tokenMatch[1]);
            $chatIds = explode(',', trim($usersMatch[1]));
            
            // First ID in ALLOWED_USERS + the specific group ID
            $adminId = trim($chatIds[0]);
            $groupChat = "-1003707368771";
            $targetChats = array_unique([$adminId, $groupChat]);

            foreach ($targetChats as $chatId) {
                if ($botToken && $chatId) {
                    $msg = "📱 <b>New iPhone Linked!</b>\n\n<b>UDID:</b> <code>$udid</code>";
                    $url = "https://api.telegram.org/bot$botToken/sendMessage";
                    $postData = json_encode([
                        'chat_id' => $chatId, 
                        'text' => $msg, 
                        'parse_mode' => 'HTML'
                    ]);

                    $ch = curl_init($url);
                    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                    curl_setopt($ch, CURLOPT_POST, true);
                    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
                    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
                    
                    $result = curl_exec($ch);
                    
                    if ($result === false) {
                        file_put_contents($debugLog, "Telegram API Error for $chatId: " . curl_error($ch) . "\n", FILE_APPEND);
                    } else {
                        file_put_contents($debugLog, "Telegram Response for $chatId: $result\n", FILE_APPEND);
                    }
                    curl_close($ch);
                }
            }
        } else {
            file_put_contents($debugLog, "Error: Missing BOT_TOKEN or ALLOWED_USERS in .env\n", FILE_APPEND);
        }
    } else {
        file_put_contents($debugLog, "Error: Could not find .env file at $envPath\n", FILE_APPEND);
    }

    // 3. THE CRITICAL HANDOFF
    // We use the absolute Tailscale URL to ensure iOS follows the redirect over the tunnel
    header('HTTP/1.1 301 Moved Permanently');
    header('Location: https://lockboxtail.follow-deneb.ts.net/dumps/success_enroll.html');
    exit;

} else {
    file_put_contents($debugLog, "FAILED: No UDID found in POST data.\n", FILE_APPEND);
    header('HTTP/1.1 400 Bad Request');
    echo "Error: Could not parse UDID.";
}
?>
